# Changelog

## [Unreleased]

### Added
- Support for modern predictable network interface names (like wlp3s0, enp2s0)
- Detection and handling of conflicting network management tools (NetworkManager, systemd-networkd, ConnMan)
- Support for nftables as an alternative to iptables
- Network connectivity verification after Wi-Fi setup
- Improved error handling and fallback mechanisms
- Support for different Alpine Linux versions

### Fixed
- Special character handling in Wi-Fi passwords
- Network interface detection for non-standard interface names
- Firewall system compatibility with nftables
- Network service restart mechanism for different init systems
- Port forwarding warning when PC_IP is not set

### Changed
- Improved interface detection to use capability-based detection
- Enhanced Wi-Fi password handling to avoid shell interpretation issues
- More robust DHCP client configuration with timeouts
- Firewall configuration to support both iptables and nftables
- Package installation to adapt to different Alpine versions