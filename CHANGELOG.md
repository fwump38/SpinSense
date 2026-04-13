# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-04-12

### Changed
- **Docker Configuration**: SpinSense Docker container now supports configuration via environment variables only. The `config.json` file is no longer required or copied into the container image.
- **Breaking Change**: Removed the mandatory `./config.json:/app/config.json` volume mount from `docker-compose.yml`. Users must now configure the container using environment variables instead of mounting a config file.
- **New Environment Variable**: Added `AUDIO_DEVICE_INDEX` environment variable for specifying audio device by index number.
- **Documentation**: Updated `README.md` and `INSTALLATION.md` to reflect environment-variable-only Docker configuration. Added comprehensive examples for Docker Compose and Portainer usage.

### Added
- Environment variable support for all audio configuration options:
  - `AUDIO_DEVICE` - audio device name or alias
  - `AUDIO_DEVICE_INDEX` - audio device index (new)
  - `AUDIO_THRESHOLD` - volume threshold for detection
  - `AUDIO_SAMPLE_LENGTH` - recording length in seconds
  - `AUDIO_SAMPLE_RATE` - sample rate in Hz
  - `SILENCE_INTERVAL` - silence timeout in seconds
  - `LOG_LEVEL` - logging verbosity

### Removed
- Mandatory `config.json` file requirement for Docker deployments
- `config.json` copy step from Dockerfile

## [0.1.0] - 2026-04-XX

Initial release of SpinSense.

### Added
- Core audio recognition engine using Shazam-compatible songrec
- Home Assistant custom integration with zeroconf discovery
- Docker container support for Raspberry Pi and x64 systems
- Web GUI for configuration and calibration
- Multi-arch Docker builds (amd64/arm64)
- Support for USB audio devices
- Real-time track metadata updates via HTTP/WebSocket</content>
<parameter name="filePath">/Users/dmirch/git/SpinSense/CHANGELOG.md