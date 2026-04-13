#!/bin/bash
set -e

# Clean up any old socket files
rm -f /tmp/spinsense.sock

# Log configuration
echo "📋 SpinSense Configuration:"
echo "  Audio Threshold: ${AUDIO_THRESHOLD:-0.015}"
echo "  Audio Sample Rate: ${AUDIO_SAMPLE_RATE:-48000} Hz"
echo "  Log Level: ${LOG_LEVEL:-INFO}"

# Check if running in standalone mode or HA integration mode
if [ "$HA_INTEGRATION_MODE" = "true" ]; then
    echo "🏠 Running in Home Assistant Integration Mode"
    echo "⚠️  Web GUI disabled. Configure via Home Assistant UI."
    # In HA mode, the integration handles the core engine
    # This entrypoint would just sleep or run a health check
    exec tail -f /dev/null
else
    echo "🚀 Starting SpinSense Core Engine (Background)..."
    # Run the engine from the root folder with environment variables
    python3 core_engine.py &
    ENGINE_PID=$!
    echo "   Core Engine PID: $ENGINE_PID"
    
    # Wait a moment for engine to start
    sleep 2
    
    echo "🚀 Starting SpinSense Web GUI (Foreground)..."
    echo "   Web UI available at: http://localhost:8000"
    
    # Move into the GUI folder so FastAPI can find the static/template folders
    cd gui
    
    # Launch FastAPI using Uvicorn, binding to all interfaces on port 8000
    # The web GUI runs in foreground, core engine in background
    exec uvicorn backend_main:app --host 0.0.0.0 --port 8000 --log-level "${LOG_LEVEL:-info}"
fi
