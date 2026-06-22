# Changelog

All notable changes to Android Panzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-06-22

### Added
- **Auto-Root Assistant**: Guided rooting workflow with background preparation of Magisk APK, platform-tools, and firmware
- **Forensic Depth Diagnosis**: 7-module deep analysis of bootloader lock, Knox, AVB, dm-verity, persist/metadata integrity, OEM/cloud locks
- **Complete Data Recovery**: SQLite unallocated record carving, WAL/Journal recovery, media thumbnail restoration
- **Rootkit & Spyware Scanner**: SUID/SGID detection, persistence mechanism scanning (init.d, post-fs-data.d, Magisk modules, Xposed hooks), open port enumeration
- **APK Static Analysis**: Binary AndroidManifest parser, signature verification, native library detection, DEX string carving for IOCs
- **Comprehensive Report Generation**: HTML, Markdown, JSON exports with SHA-256 manifest validation
- **137 Unit Tests**: Mock ADB testing, parser validation against real APKs, security quoting tests

### Security
- **Command Injection Prevention**: All shell invocations wrapped with `shq()` / `shlex.quote()`
- **Honest Capability Badges**: Functions marked as `[ADB]`, `[ROOT]`, `[SDR/HW]`, `[INFO]`, `[GEFAHR]` — no data fabrication
- **Pure Python Core**: No external dependencies for base functionality, optional features via `requirements-optional.txt`

### Documentation
- **450+ Functions** across 45 categories clearly documented
- **Root Arsenal** detailed with forensic depth explanation
- **Badge system** explaining what's real vs. what requires hardware/lab equipment
- GitHub Actions CI, CONTRIBUTING guide, Pull Request template

## [1.0.0] - Initial Release

### Features
- Device auto-detection and root status recognition
- Dashboard with hardware/OS/battery/network analysis
- Deep forensic acquisition (45 sections)
- Messenger/email forensics, WLAN credential recovery
- Custom ROM/recovery discovery
- Automated mode switching (Fastboot/Download/Recovery)
- Traffic capture and analysis
- Comprehensive terminal UI (banner, menus, pagers)

---

For migration guides, security advisories, and detailed technical changes, see GitHub [Releases](https://github.com/ADAOKL/android-panzer/releases).
