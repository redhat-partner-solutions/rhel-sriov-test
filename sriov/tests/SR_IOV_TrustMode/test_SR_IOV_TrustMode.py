import time
from sriov.common.utils import *


def test_SR_IOV_TrustMode(dut, settings):
    """Test and ensure that VF trust mode functions as intended

    Args:
        dut:      ssh connection obj
        settings: settings obj
    """

    mac_1 = "aa:bb:cc:dd:ee:11"
    mac_2 = "aa:bb:cc:dd:ee:22"
    mac_3 = "aa:bb:cc:dd:ee:33"
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {mac_1}",
        f"ip link set {pf} vf 0 trust on",
        f"ip link set {pf}v0 address {mac_2}",
        f"ip link set {pf}v0 up",
    ]

    create_vfs(dut, pf, 1)

    execute_and_assert(dut, steps, 0, 0.1)

    # check if vf 0 mac address is equal to mac_2
    cmd = ["ip link show {}".format(pf) + " | awk '/vf 0/{print $4;}'"]
    outs, errs = execute_and_assert(dut, cmd, 0)
    vf_mac = outs[0][0].strip("\n")
    print(vf_mac)
    assert vf_mac == mac_2

    # set trust mode to off
    cmd = ["ip link set {}".format(pf) + " vf 0 trust off"]
    execute_and_assert(dut, cmd, 0)

    # try to overwrite mac_2 with mac_3
    cmd = "ip link set {}".format(pf) + "v0 address {}".format(mac_3)
    print(cmd)
    code, out, err = dut.execute(cmd)
    if code != 0:
        print(err[0].strip("\n"))

    # check if vf 0 mac address is NOT equal to mac_3
    cmd = ["ip link show {}".format(pf) + " | awk '/vf 0/{print $4;}'"]
    outs, errs = execute_and_assert(dut, cmd, 0)
    vf_mac = outs[0][0].strip("\n")
    print(vf_mac)
    assert vf_mac != mac_3
