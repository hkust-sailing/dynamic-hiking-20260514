from dataclasses import dataclass

@dataclass
class IpSetting:
    """IP and Port"""
    local_ip: str = "192.168.0.131"
    local_port: int = 10000
    remote_ip: str = "192.168.0.125"
    remote_port: int = 5000