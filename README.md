# 💿 SpinSense
Integrate your analogue record player into your digital life. This tool uses audio recognition and MQTT to create a media player entity for Home Assistant to show the song currently spinning on your turntable. 

## ✨ Features
- Automatic ID: Powered by songrec (Shazam-compatible) for high-accuracy track recognition.

- MQTT-backed media player: Home Assistant receives track metadata via MQTT and exposes it as a media_player entity.

- Separate Audio Engine: The HA custom integration consumes MQTT metadata, while the Pi Zero runs the audio recognition engine.

- Multi-Arch Ready: Runs natively on Raspberry Pi (ARM) near your deck or on your main NAS (x64).

- Guided Onboarding: A built-in Web GUI to help you calibrate your "Silence vs. Music" thresholds.

## 🚀 How It Works
- SpinSense doesn't just "guess." It monitors the RMS volume of your input device. When the needle drops:

  - Detection: It identifies a rise in volume above your calibrated THRESHOLD.

  - Recognition: It captures a 10-second high-fidelity sample and identifies it.

  - Communication: It publishes the Artist, Album, and Title to your MQTT Broker.

  - Silence Logic: When the side ends or the record is stopped, it waits for a SILENCE_LIMIT before marking the player as Stopped.

## 🛠 Project Structure

This project is built to be modular and Docker-first:

/core: The Python-based recognition engine.

/gui: A lightweight Flask/FastAPI web interface for configuration.

/docker: Multi-arch build files for Pi and NAS compatibility.

## 🏗 Installation

SpinSense includes both a standalone recognition engine and a Home Assistant custom integration:

- `custom_components/spinsense/` is the HA custom integration.
- `core_engine.py` is the standalone audio recognition engine.

### Home Assistant Installation via HACS

This repository is HACS-ready. To install it with HACS:

1. In Home Assistant, open HACS.
2. Go to `Integrations` → `+ Explore & add repositories`.
3. Add this repository URL: `https://github.com/fwump38/SpinSense`.
4. Install `SpinSense` from HACS and restart Home Assistant.

For complete installation steps, see [INSTALLATION.md](INSTALLATION.md).

