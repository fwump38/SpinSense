import asyncio
import json
import os
import numpy as np
import sounddevice as sd
import paho.mqtt.client as mqtt
from shazamio import Shazam

# --- 1. Load Configuration ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Extract config vars
THRESHOLD = config['Audio']['Volume_Threshold']
SILENCE_LIMIT = config['Audio']['Song_Sample_Length'] # Assuming this acts as interval for now
SAMPLE_LEN = config['Audio']['Song_Sample_Length']

MQTT_HOST = config['MQTT']['Broker']['Host']
MQTT_USER = config.get('MQTT', {}).get('Broker', {}).get('User', 'vinylrecord') # Safe fallback
MQTT_PASS = config.get('MQTT', {}).get('Broker', {}).get('Password', 'C0C0nut1')
MQTT_PORT = config['MQTT']['Broker']['Port']

# --- Dynamically Build Topics ---
BASE_TOPIC = "home/vinyl"
TOPIC_STATE = f"{BASE_TOPIC}/state"
TOPIC_TITLE = f"{BASE_TOPIC}/title"
TOPIC_ARTIST = f"{BASE_TOPIC}/artist"
TOPIC_ARTART = f"{BASE_TOPIC}/album_art"
LEGACY_TOPIC = f"{BASE_TOPIC}/now_playing"
DISCOVERY_TOPIC = "homeassistant/media_player/vinyl_pi/config"

# --- 2. MQTT Setup ---
mqtt_client = mqtt.Client()
if MQTT_USER and MQTT_PASS:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
mqtt_client.loop_start()

def announce_to_ha():
    """Publishes the Home Assistant Discovery Payload."""
    payload = {
        "name": "Vinyl Record Player",
        "unique_id": "vinyl_pi_record_player",
        "device_class": "speaker",
        "state_topic": TOPIC_STATE, 
        "json_attributes_topic": LEGACY_TOPIC, 
        "payload_play": "playing",
        "payload_stop": "stopped",
        "payload_idle": "idle"
    }
    mqtt_client.publish(DISCOVERY_TOPIC, json.dumps(payload), retain=True)

def publish_state(status, artist="", title="", album="", art_url=""):
    """Publishes state to split topics and legacy JSON topic."""
    mqtt_client.publish(TOPIC_STATE, status, retain=True)
    mqtt_client.publish(TOPIC_TITLE, title, retain=True)
    mqtt_client.publish(TOPIC_ARTIST, artist, retain=True)
    mqtt_client.publish(TOPIC_ARTART, art_url, retain=True)

    payload = json.dumps({
        "status": status,
        "artist": artist,
        "title": title,
        "album": album,
        "art_url": art_url
    })
    mqtt_client.publish(LEGACY_TOPIC, payload, retain=True)

# --- 3. Shazam & Audio Logic ---
shazam = Shazam()
state = {
    "in_song": False,
    "last_song": "",
    "silence_counter": 0,
    "current_rms": 0.0
}

async def recognize_audio():
    """Records audio and identifies it via Shazam."""
    print(f"\n[!] Music detected. Recording {SAMPLE_LEN}s for identification...")
    
    recording = sd.rec(int(SAMPLE_LEN * 48000), samplerate=48000, channels=1, dtype='float32')
    sd.wait() 
    
    audio_bytes = (recording * 32767).astype(np.int16).tobytes()
    
    print("[!] Analyzing with Shazam...")
    out = await shazam.recognize_song(audio_bytes)
    
    if 'track' in out:
        track = out['track']
        title = track.get('title', 'Unknown Title')
        artist = track.get('subtitle', 'Unknown Artist')
        
        art_url = track.get('images', {}).get('coverarthq', track.get('images', {}).get('coverart', ''))
        
        album = "Unknown Album"
        for section in track.get('sections', []):
            if section.get('type') == 'SONG':
                for meta in section.get('metadata', []):
                    if meta.get('title') == 'Album':
                        album = meta.get('text')
        
        result_str = f"{artist} - {title}"
        
        if result_str != state["last_song"]:
            print(f"🎵 NEW TRACK: {result_str} (Album: {album})")
            publish_state("stopped")
            await asyncio.sleep(0.5)
            publish_state("playing", artist, title, album, art_url)
            state["last_song"] = result_str
        else:
            print(f"      (Confirmed same track: {state['last_song']})")
            publish_state("playing", artist, title, album, art_url)
            
        state["in_song"] = True
    else:
        print("❌ Could not identify track.")
        
    state["silence_counter"] = 0

async def audio_monitor_loop():
    """Continuous loop monitoring microphone RMS."""
    announce_to_ha()
    print(f"--- VINYL SCROBBLER ALPHA ACTIVE (Threshold: {THRESHOLD}) ---")
    
    def audio_callback(indata, frames, time, status):
        rms = np.sqrt(np.mean(indata**2))
        state["current_rms"] = float(rms)

    stream = sd.InputStream(samplerate=48000, channels=1, callback=audio_callback)
    with stream:
        while True:
            vol = state["current_rms"]
            
            try:
                if os.path.exists('/tmp/spinsense.sock'):
                    reader, writer = await asyncio.open_unix_connection('/tmp/spinsense.sock')
                    payload = json.dumps({
                        "type": "live_status",
                        "payload": {
                            "rms_level": vol,
                            "engine_active": True,
                            "status_msg": "Listening",
                            "track": {"title": state["last_song"]}
                        }
                    }) + "\n"
                    writer.write(payload.encode())
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
            except Exception:
                pass 
            
            if vol > THRESHOLD:
                if not state["in_song"] or state["silence_counter"] > 0:
                    stream.stop()
                    await recognize_audio()
                    stream.start()
                else:
                    print(".", end="", flush=True)
            else:
                if state["in_song"]:
                    state["silence_counter"] += 1
                    print("s", end="", flush=True)
                    
                    if state["silence_counter"] >= SILENCE_LIMIT:
                        print(f"\n[ STOPPED ] {SILENCE_LIMIT}s silence limit reached.")
                        publish_state("stopped")
                        state["in_song"] = False
                        state["last_song"] = ""
                        state["silence_counter"] = 0
                        
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(audio_monitor_loop())
    except KeyboardInterrupt:
        print("\nShutting down...")
        mqtt_client.loop_stop()