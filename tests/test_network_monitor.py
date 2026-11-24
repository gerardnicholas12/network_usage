from collections import namedtuple
from core.network_monitor import calculate_throughput, NetworkMonitor

Counters=namedtuple("Counters","bytes_sent bytes_recv")
def test_throughput_conversion():
    up,down=calculate_throughput(Counters(100,200),Counters(1_000_100,2_000_200),2)
    assert up==4 and down==8

def test_counter_reset_clamped():
    assert calculate_throughput(Counters(100,200),Counters(50,100),2)==(0,0)

def test_invalid_ping_target():
    assert NetworkMonitor().ping("bad target && cmd") is None

