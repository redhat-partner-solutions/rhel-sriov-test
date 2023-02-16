import pytest
import time
from sriov.common.utils import create_vfs, execute_and_assert


@pytest.mark.parametrize("spoof", ("on", "off"))
@pytest.mark.parametrize("trust", ("on", "off"))
@pytest.mark.parametrize("qos", (True, False))
@pytest.mark.parametrize("vlan", (True, False))
@pytest.mark.parametrize("max_tx_rate", (True, False))
def test_SR_IOV_InterVF_IPv6(
    dut, settings, testdata, spoof, trust, qos, vlan, max_tx_rate
):
    """Test and ensure that VFs on the same PF can communicate with each other via IPv6

    Args:
        dut:         ssh connection obj
        settings:    settings obj
        testdata:    testdata obj
        spoof:       spoof parameter
        trust:       trust parameter
        qos:         qos parameter
        vlan:        vlan parameter
        max_tx_rate: max_tx_rate parameter
    """

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    ipv6_prefix = testdata.dut_ip_v6
    mac_prefix = "aa:bb:cc:dd:ee:0"

    steps = []
    for i in range(2):
        steps.extend(
            [
                f"ip netns add ns{i}",
                f"ip link set {pf} vf {i} mac {mac_prefix}{i}",
                f"ip link set {pf} vf {i} spoof {spoof}",
                f"ip link set {pf} vf {i} trust {trust}",
            ]
        )
        if vlan:
            qos_str = f"qos {testdata.qos}" if qos else ""
            steps.append(f"ip link set {pf} vf {i} vlan {testdata.vlan} {qos_str}")
        if max_tx_rate:
            steps.append(f"ip link set {pf} vf {i} max_tx_rate {testdata.max_tx_rate}")
        steps.append(f"ip link set {pf}v{i} netns ns{i}")
        steps.append(
            f"ip netns exec ns{i} ip -6 addr add {ipv6_prefix}{i}/64 dev {pf}v{i}"
        )
        steps.append(f"ip netns exec ns{i} ip link set {pf}v{i} up")

    assert create_vfs(dut, pf, 2)
    execute_and_assert(dut, steps, 0, 0.1)

    # Wait for ipv6 neighbor entry populated
    time.sleep(3)
    steps = [
        f"ip netns exec ns0 ping -6 -W 1 -c 1 {ipv6_prefix}1",
        "ip netns del ns0",
        "ip netns del ns1",
    ]
    execute_and_assert(dut, steps, 0)
