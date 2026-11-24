import re, socket, subprocess, time
from dataclasses import dataclass
from datetime import datetime
import psutil


def calculate_throughput(previous, current, elapsed):
    if elapsed <= 0: return 0.0,0.0
    sent=max(0,current.bytes_sent-previous.bytes_sent); received=max(0,current.bytes_recv-previous.bytes_recv)
    return sent*8/elapsed/1_000_000, received*8/elapsed/1_000_000


@dataclass
class NetworkMonitor:
    timeout: int = 5

    def interfaces(self):
        return [name for name, stats in psutil.net_if_stats().items() if stats.isup]

    def counters(self, interface):
        return psutil.net_io_counters(pernic=True).get(interface)

    def run_command(self, args):
        try:
            return subprocess.run(args,capture_output=True,text=True,timeout=self.timeout,check=False,encoding="utf-8",errors="replace").stdout
        except (OSError,subprocess.SubprocessError): return ""

    def wifi_details(self):
        text=self.run_command(["netsh","wlan","show","interfaces"]); details={}
        for key,label in [("ssid","SSID"),("signal","Signal"),("channel","Channel"),("receive_rate","Receive rate (Mbps)"),("transmit_rate","Transmit rate (Mbps)")]:
            match=re.search(rf"^\s*{re.escape(label)}\s*:\s*(.+)$",text,re.MULTILINE|re.IGNORECASE)
            details[key]=match.group(1).strip() if match else None
        return details

    def local_ip(self):
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s: s.connect(("192.0.2.1",80)); return s.getsockname()[0]
        except OSError: return "Unavailable"

    def ping(self, host="1.1.1.1"):
        if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}",host): return None
        text=self.run_command(["ping","-n","1","-w",str(self.timeout*1000),host])
        match=re.search(r"(?:time[=<]|Average = )\s*(\d+)ms",text,re.IGNORECASE); return float(match.group(1)) if match else None

