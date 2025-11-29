# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-29

### Added
- Initial release as standalone repository
- Full support for KDC101, KBD101, TDC001, KIM101, KPZ101, TPZ001 controllers
- Kinesis .NET backend with pythonnet
- APT COM fallback backend
- Automatic device discovery
- Stage auto-detection from EEPROM
- PyQt5-based GUI with:
  - Device tree view
  - Per-device control tabs
  - Multi-channel KIM101 support
  - Built-in testing interface
  - Configuration persistence
- Comprehensive test suites (88+ tests)
- Full API documentation
- Screenshot capture tools for documentation

### Controllers
- **KDC101** - K-Cube DC Servo Motor Driver
- **KBD101** - K-Cube Brushless DC Motor Driver  
- **TDC001** - T-Cube DC Servo Motor Driver (Legacy)
- **KIM101** - K-Cube Inertial Motor Driver (4-channel)
- **KPZ101** - K-Cube Piezo Driver
- **TPZ001** - T-Cube Piezo Driver (Legacy)

### Documentation
- Comprehensive README with installation instructions
- GUI documentation with screenshots
- Hardware manuals included in docs/manuals/
- API reference for all controllers

## [Unreleased]

### Planned
- XA software backend support (newer Thorlabs platform)
- Additional controller support (BSC201, BBD series)
- Linux support via Wine/Mono
- Async/await API for non-blocking operations
