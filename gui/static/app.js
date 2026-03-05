console.log("1. app.js file loaded successfully!");

document.addEventListener("DOMContentLoaded", () => {
    console.log("2. Web page elements loaded. Starting connections...");
    
    // --- 1. WebSocket Connection ---
    const wsUrl = `ws://${window.location.host}/ws/live-status`;
    console.log("3. Attempting to connect to WebSocket at:", wsUrl);
    
    const socket = new WebSocket(wsUrl);
    window.socket = socket; // This exposes 'socket' so your console command works!

    socket.onopen = () => console.log("✅ WebSocket Connected!");
    socket.onerror = (err) => console.error("❌ WebSocket Error:", err);
    socket.onclose = () => console.log("⚠️ WebSocket Closed.");

    const volBar = document.getElementById('volume-bar');
    const volText = document.getElementById('volume-text');
    const trackTitle = document.getElementById('track-title');

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "live_status") {
            const payload = data.payload;
            let percent = Math.min(payload.rms_level * 1000, 100);
            
            if (volBar) volBar.style.width = `${percent}%`;
            if (volText) volText.textContent = payload.rms_level.toFixed(4);
            if (trackTitle) trackTitle.textContent = payload.track.title;
        }
    };

    // --- 2. Load Devices ---
    console.log("4. Fetching audio devices...");
    fetch('/api/devices')
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            console.log("✅ Devices loaded:", data);
            const select = document.getElementById('mic-device');
            data.devices.forEach(dev => {
                const opt = document.createElement('option');
                opt.value = dev.name;
                opt.textContent = dev.name;
                select.appendChild(opt);
            });
        })
        .catch(err => console.error("❌ Failed to load devices:", err));

    // --- 3. Load Config ---
    console.log("5. Fetching configuration...");
    fetch('/api/config')
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(config => {
            console.log("✅ Config loaded:", config);
            document.getElementById('vol-threshold').value = config.Audio.Volume_Threshold;
            document.getElementById('sample-len').value = config.Audio.Song_Sample_Length;
            document.getElementById('mqtt-host').value = config.MQTT.Broker.Host;
            document.getElementById('mqtt-port').value = config.MQTT.Broker.Port;
            
            // Wait 100ms for the device dropdown to populate before setting its value
            setTimeout(() => {
                const micSelect = document.getElementById('mic-device');
                if (micSelect && micSelect.querySelector(`option[value="${config.Hardware.Mic_Device}"]`)) {
                    micSelect.value = config.Hardware.Mic_Device;
                }
            }, 100);
        })
        .catch(err => console.error("❌ Failed to load config:", err));
});