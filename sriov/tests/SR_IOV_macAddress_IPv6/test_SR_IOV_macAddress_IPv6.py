from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    execute_until_timeout,
)


def test_SR_IOV_macAddress_IPv6(dut, trafficgen, settings, testdata):
    """Test and ensure that VF admin MAC address functions as intended with IPv6

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """

    trafficgen_ip_v6 = testdata.trafficgen_ip_v6
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    dut_ip_v6 = testdata.dut_ip_v6
    vf0_mac = testdata.dut_mac
    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    steps = [
        f"ip -6 add del {trafficgen_ip_v6}/64 dev {trafficgen_pf} 2>/dev/null || true",
        f"ip -6 neigh del {dut_ip_v6}  dev {trafficgen_pf} || true",
        f"ip -6 add add {trafficgen_ip_v6}/64 dev {trafficgen_pf}",
    ]

    execute_and_assert(trafficgen, steps, 0, 0.1)

    create_vfs(dut, pf, 1)

    steps = [
        f"ip -6 neigh del {trafficgen_ip_v6} dev {pf} || true",
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {vf0_mac}",
        f"ip link set {pf}v0 up",
        f"ip -6 add add {dut_ip_v6}/64 dev {pf}v0",
    ]

    execute_and_assert(dut, steps, 0, 0.1)

    ping_cmd = "ping -6 -W 1 -c 1 {}".format(testdata.dut_ip_v6)
    assert execute_until_timeout(trafficgen, ping_cmd)
