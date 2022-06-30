import time
from sriov.common.utils import *

def test_SR_IOV_TrustMode(dut, settings):
    mac_1 = "aa:bb:cc:dd:ee:11"
    mac_2 = "aa:bb:cc:dd:ee:22"
    mac_3 = "aa:bb:cc:dd:ee:33"
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        "echo 0 > /sys/class/net/{}/device/sriov_numvfs".format(pf),
        "echo 1 > /sys/class/net/{}/device/sriov_numvfs".format(pf),
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {mac_1}",
        f"ip link set {pf} vf 0 trust on",
        f"ip link set {pf}v0 address {mac_2}",
        f"ip link set {pf}v0 up"
        ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    # check if vf 0 mac address is equal to mac_2
    cmd = "ip link show {}".format(pf) + " | awk '/vf 0/{print $4;}'"
    code, out, err = dut.execute(cmd)
    assert code == 0, err
    vf_mac = out[0].strip("\n")
    assert vf_mac == mac_2
    
    # set trust mode to on
    steps = [
        f"ip link set {pf} vf 0 trust off",
        f"ip link set {pf}v0 address {mac_3}"
        ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)
        
    # check if vf 0 mac address is NOT equal to mac_3
    cmd = "ip link show {}".format(pf) + " | awk '/vf 0/{print $4;}'"
    code, out, err = dut.execute(cmd)
    assert code == 0, err
    vf_mac = out[0].strip("\n")
    assert vf_mac != mac_3    
