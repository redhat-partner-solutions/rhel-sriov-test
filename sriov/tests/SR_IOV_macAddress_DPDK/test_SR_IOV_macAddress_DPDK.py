from sriov.common.utils import (
    create_vfs,
    get_pci_address,
    execute_and_assert,
    bind_driver,
    prepare_ping_test,
    execute_until_timeout,
)


def test_SR_IOV_macAddress_DPDK(dut, trafficgen, settings, testdata):
    """Test and ensure that VF MAC address functions as intended when bound
       to the DPDK driver

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_ip = testdata.trafficgen_ip
    dut_ip = testdata.dut_ip
    vf0_mac = testdata.dut_mac
    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    assert create_vfs(dut, pf, 1)

    cmd = ["ip link set {} vf 0 mac {}".format(pf, vf0_mac)]
    execute_and_assert(dut, cmd, 0)

    vf_pci = get_pci_address(dut, pf + "v0")
    assert bind_driver(dut, vf_pci, "vfio-pci")

    print(testdata.container_cmd)
    dut.start_testpmd(testdata.container_cmd)
    assert dut.testpmd_active()

    steps = ["set fwd icmpecho", "start"]
    for step in steps:
        code = dut.testpmd_cmd(step)
        assert code == 0

    trafficgen_vlan = 0
    trafficgen_mac = None  # None means no need to set arp entry on DUT
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

    ping_cmd = "ping -W 1 -c 1 {}".format(dut_ip)
    assert execute_until_timeout(trafficgen, ping_cmd)
