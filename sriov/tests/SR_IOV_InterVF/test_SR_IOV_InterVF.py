import pytest
import time
from sriov.common.utils import *


@pytest.mark.parametrize('spoof', ("on", "off"))
@pytest.mark.parametrize('trust', ("on", "off"))
@pytest.mark.parametrize('qos', (True, False))
@pytest.mark.parametrize('vlan', (True, False))
@pytest.mark.parametrize('max_tx_rate', (True, False))
def test_SR_IOV_InterVF(dut, trafficgen, settings, testdata, spoof,
                        trust, qos, vlan, max_tx_rate):
    """ Test and ensure that VFs on the same PF can communicate with each other

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
        spoof:       spoof parameter
        trust:       trust parameter
        qos:         qos parameter
        vlan:        vlan parameter
        max_tx_rate: max_tx_rate parameter
    """
    set_pipefail(dut)

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    ip_addr_prefix = "100.1.1.1"
    mac_prefix = "aa:bb:cc:dd:ee:0"
    steps = [
        f"echo 0 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"echo 2 > /sys/class/net/{pf}/device/sriov_numvfs",
    ]
    for i in range(2):
        steps.extend([
            f"ip netns add ns{i}",
            f"ip link set {pf} vf {i} mac {mac_prefix}{i}",
            f"ip link set {pf} vf {i} spoof {spoof}",
            f"ip link set {pf} vf {i} trust {trust}",
        ])
        if vlan:
            qos_str = f"qos {testdata['qos']}" if qos else ""
            steps.append(
                f"ip link set {pf} vf {i} vlan {testdata['vlan']} {qos_str}")
        if max_tx_rate:
            steps.append(
                f"ip link set {pf} vf {i} max_tx_rate {testdata['max_tx_rate']}")
        steps.append(f"ip link set {pf}v{i} netns ns{i}")
        steps.append(
            f"ip netns exec ns{i} ip addr add {ip_addr_prefix}{i}/24 dev {pf}v{i}")
        steps.append(f"ip netns exec ns{i} ip link set {pf}v{i} up")

    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    dut.execute(f"ip netns exec ns0 arp -s {ip_addr_prefix}1 {mac_prefix}1")
    dut.execute(f"ip netns exec ns1 arp -s {ip_addr_prefix}0 {mac_prefix}0")
    code, out, err = dut.execute(
        f"ip netns exec ns0 ping -W 1 -c 1 {ip_addr_prefix}1")
    dut.execute("ip netns del ns0")
    dut.execute("ip netns del ns1")
    assert code == 0, err
