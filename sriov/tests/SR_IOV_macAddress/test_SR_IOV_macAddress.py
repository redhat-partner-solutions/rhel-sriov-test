from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    prepare_ping_test,
    execute_until_timeout,
)


def test_SR_IOV_macAddress(dut, trafficgen, settings, testdata):
    """Test and ensure that VF MAC address functions as intended

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """

    trafficgen_ip = testdata.trafficgen_ip
    dut_ip = testdata.dut_ip
    vf0_mac = testdata.dut_mac
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        "ip link set {}v0 down".format(pf),
        "ip link set {} vf 0 mac {}".format(pf, vf0_mac),
        "ip link set {}v0 up".format(pf),
        "ip add add {}/24 dev {}v0".format(dut_ip, pf),
    ]

    create_vfs(dut, pf, 1)

    execute_and_assert(dut, steps, 0, 0.1)

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    trafficgen_vlan = 0
    assert prepare_ping_test(
        trafficgen,
        trafficgen_pf,
        trafficgen_vlan,
        trafficgen_ip,
        trafficgen_mac,
        dut,
        dut_ip,
        vf0_mac,
        testdata,
    )

    ping_cmd = "ping -W 1 -c 1 {}".format(testdata.dut_ip)
    assert execute_until_timeout(trafficgen, ping_cmd)
