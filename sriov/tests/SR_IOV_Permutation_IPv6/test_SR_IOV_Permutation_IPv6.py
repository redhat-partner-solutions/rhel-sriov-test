import pytest
from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    execute_until_timeout,
    delete_ipv6_neighbor,
    prepare_ping_ipv6_test,
)


@pytest.mark.parametrize("spoof", ("on", "off"))
@pytest.mark.parametrize("trust", ("on", "off"))
@pytest.mark.parametrize("qos", (True, False))
@pytest.mark.parametrize("vlan", (True, False))
@pytest.mark.parametrize("max_tx_rate", (True, False))
def test_SR_IOV_Permutation_IPv6(
    dut, trafficgen, settings, testdata, spoof, trust, qos, vlan, max_tx_rate
):
    """Test VFs function with various properties

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

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    dut_ip_v6 = testdata.dut_ip_v6
    trafficgen_ip_v6 = testdata.trafficgen_ip_v6
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_vlan = testdata.vlan if vlan else 0

    delete_ipv6_neighbor(dut, trafficgen_ip_v6)
    delete_ipv6_neighbor(trafficgen, dut_ip_v6)

    steps = [
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {testdata.dut_mac}",
        f"ip link set {pf} vf 0 spoof {spoof}",
        f"ip link set {pf} vf 0 trust {trust}",
    ]
    if vlan:
        qos_str = f"qos {testdata.qos}" if qos else ""
        steps.append(f"ip link set {pf} vf 0 vlan {testdata.vlan} {qos_str}")
    if max_tx_rate:
        steps.append(f"ip link set {pf} vf 0 max_tx_rate {testdata.max_tx_rate}")
    steps.append(f"ip -6 addr add {dut_ip_v6}/64 dev {pf}v0")
    steps.append(f"ip link set {pf}v0 up")

    create_vfs(dut, pf, 1)

    execute_and_assert(dut, steps, 0, 0.1)

    prepare_ping_ipv6_test(trafficgen, trafficgen_pf, trafficgen_vlan,
                           trafficgen_ip_v6, dut_ip_v6, testdata)

    assert execute_until_timeout(trafficgen, f"ping -W 1 -c 1 {dut_ip_v6}")
