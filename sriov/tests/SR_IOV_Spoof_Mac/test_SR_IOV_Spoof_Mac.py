import time
import pytest
from sriov.common.utils import *

@pytest.mark.parametrize('spoof', ("on", "off"))
def test_SR_IOV_Spoof_Mac(dut, trafficgen, settings, testdata, spoof):
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        f"echo 0 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"echo 1 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {testdata['dut_mac']}",
        f"ip link set {pf} vf 0 spoof {spoof}",
        f"ip add add {testdata['dut_ip']}/24 dev {pf}v0",
        f"ip link set {pf}v0 up"
        ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)
    
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    spoof_mac = testdata['dut_spoof_mac']
    trafficgen_ip = testdata['trafficgen_ip']
    tmux_session = testdata['tmux_session_name']
    tmux_cmd = f"timeout 3 nping --dest-mac {trafficgen_mac} --source-mac {spoof_mac} {trafficgen_ip}"
    print(tmux_cmd)
    start_tmux(dut, tmux_session, tmux_cmd)
    tgen_cmd = f"timeout 3 tcpdump -i {trafficgen_pf} -c 1 ether host {spoof_mac}"
    print(tgen_cmd)
    code, out, err = trafficgen.execute(tgen_cmd)
    stop_tmux(dut, tmux_session)
    if spoof == "off":
        assert code == 0, err
    else:
        assert code != 0, err
    
