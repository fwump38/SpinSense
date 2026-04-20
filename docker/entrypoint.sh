#!/bin/bash
set -e

echo "SpinSense Configuration:"
echo "  Audio Threshold: ${AUDIO_THRESHOLD:-0.015}"
echo "  Audio Sample Rate: ${AUDIO_SAMPLE_RATE:-48000} Hz"
echo "  Log Level: ${LOG_LEVEL:-INFO}"

echo "Starting SpinSense..."
echo "  Web UI available at: http://localhost:8000"

# Single process: FastAPI + engine as async task
exec uvicorn gui.backend_main:app --host 0.0.0.0 --port 8000 --log-level "${LOG_LEVEL:-info}"
