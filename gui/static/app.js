document.addEventListener('DOMContentLoaded', async () => {

    // --- Helper: Update Engine Status Badge ---
    function updateEngineControls(statusMsg, engineActive) {
        const badge = document.getElementById('engine-status-badge');
        const normalized = String(statusMsg || '').toLowerCase();

        if (normalized === 'playing') {
            badge.innerText = 'Engine: Playing';
            badge.className = 'badge success';
        } else if (normalized === 'stopped' || !engineActive) {
            badge.innerText = 'Engine: Stopped';
            badge.className = 'badge stopped';
        } else {
            badge.innerText = 'Engine: Listening';
            badge.className = 'badge warning';
        }
    }

    // --- Helper: Update Now-Playing section ---
    function updateTrackMetadata(payload) {
        if (payload.track && payload.track.title) {
            document.getElementById('track-title').innerText = payload.track.title;
            document.getElementById('track-artist').innerText = payload.track.artist || 'Unknown Artist';
            document.getElementById('track-album').innerText = payload.track.album || 'Unknown Album';

            const artImg = document.getElementById('album-art');
            if (payload.track.art_url) {
                artImg.src = payload.track.art_url;
            }
        } else if (normalized(payload.status_msg) !== 'playing') {
            document.getElementById('track-title').innerText = 'Waiting for drop...';
            document.getElementById('track-artist').innerText = 'Artist';
            document.getElementById('track-album').innerText = 'Album';
            document.getElementById('album-art').src = '/static/placeholder.jpg';
        }
    }

    function normalized(s) {
        return String(s || '').toLowerCase();
    }

    // --- 1. WebSocket Connection (Live Data) with auto-reconnect ---
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/live-status`;

    let ws = null;
    let reconnectDelay = 1000;

    function connectWebSocket() {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            reconnectDelay = 1000;
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'rms_update') {
                    // Fast path: only update the RMS meter (~5 Hz)
                    const rms = data.payload.rms_level;
                    document.getElementById('volume-text').innerText = rms.toFixed(4);
                    const percent = Math.min((rms / 0.05) * 100, 100);
                    document.getElementById('volume-bar').style.width = `${percent}%`;

                } else if (data.type === 'live_status') {
                    const payload = data.payload;

                    if (payload.rms_level !== undefined) {
                        document.getElementById('volume-text').innerText = payload.rms_level.toFixed(4);
                        const percent = Math.min((payload.rms_level / 0.05) * 100, 100);
                        document.getElementById('volume-bar').style.width = `${percent}%`;
                    }

                    updateTrackMetadata(payload);
                    updateEngineControls(payload.status_msg, payload.engine_active);
                }
            } catch (error) {
                console.error('WebSocket payload error:', error);
            }
        };

        ws.onclose = () => {
            setTimeout(() => {
                reconnectDelay = Math.min(reconnectDelay * 2, 30000);
                connectWebSocket();
            }, reconnectDelay);
        };

        ws.onerror = () => {
            ws.close();
        };
    }

    connectWebSocket();

    // --- 2. Load Config & Devices ---
    async function loadConfigAndDevices() {
        try {
            const devRes = await fetch('/api/devices');
            const devData = await devRes.json();
            const select = document.getElementById('mic-device');
            select.innerHTML = '';

            const defaultOpt = document.createElement('option');
            defaultOpt.value = "default";
            defaultOpt.textContent = "System Default";
            select.appendChild(defaultOpt);

            devData.devices.forEach(device => {
                const opt = document.createElement('option');
                opt.value = device.name;
                opt.textContent = device.name;
                select.appendChild(opt);
            });
        } catch (error) {
            console.error("Failed to load devices:", error);
        }

        try {
            const confRes = await fetch('/api/config');
            const config = await confRes.json();

            if (config.device_name) {
                document.getElementById('mic-device').value = config.device_name;
            }
            if (config.threshold !== undefined) {
                document.getElementById('vol-threshold').value = config.threshold;
            }
            if (config.sample_length !== undefined) {
                document.getElementById('sample-len').value = config.sample_length;
            }
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    async function loadStatus() {
        try {
            const res = await fetch('/api/status');
            const status = await res.json();

            if (status.rms_level !== undefined) {
                document.getElementById('volume-text').innerText = status.rms_level.toFixed(4);
                let percent = Math.min((status.rms_level / 0.05) * 100, 100);
                document.getElementById('volume-bar').style.width = `${percent}%`;
            }

            updateTrackMetadata(status);
            updateEngineControls(status.status_msg, status.engine_active);
        } catch (error) {
            console.error('Failed to load engine status:', error);
        }
    }

    // --- 3. Save Config Button ---
    document.getElementById('btn-save-config').addEventListener('click', async () => {
        const configPayload = {
            threshold: parseFloat(document.getElementById('vol-threshold').value),
            sample_length: parseFloat(document.getElementById('sample-len').value),
        };

        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configPayload)
        });

        const btn = document.getElementById('btn-save-config');
        btn.innerText = "Saved!";
        setTimeout(() => { btn.innerText = "Save Settings"; }, 2000);
    });

    // Initialize everything on page load
    await loadStatus();
    await loadConfigAndDevices();
});