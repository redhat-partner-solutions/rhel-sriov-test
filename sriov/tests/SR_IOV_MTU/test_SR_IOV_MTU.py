import re
import pytest
from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    set_mtu,
    prepare_ping_test,
    execute_until_timeout,
    get_vf_mac,
    switch_detected,
)


def test_SR_IOV_MTU(dut, trafficgen, settings, testdata):
    """Test and ensure that VF MTU functions as intended

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """

    dut_ip = testdata.dut_ip
    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    if switch_detected(dut, pf) and "mtu" not in settings.config:
        pytest.skip("Switch detected but mtu is not defined")

    assert create_vfs(dut, pf, 1)

    # command to get the maxmtu from the DUT
    cmd = [f"ip -d link list {pf}"]
    outs, errs = execute_and_assert(dut, cmd, 0)
    dut_mtu = 0
    for line in outs[0]:
        match = re.search(r"maxmtu (\d+)", line)
        if match is not None:
            dut_mtu = int(match.group(1))
            break
    assert dut_mtu != 0

    # get trafficgen maxmtu
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mtu = 0
    cmd = [f"ip -d link list {trafficgen_pf}"]
    outs, errs = execute_and_assert(trafficgen, cmd, 0)
    for line in outs[0]:
        match = re.search(r"maxmtu (\d+)", line)
        if match is not None:
            trafficgen_mtu = int(match.group(1))
            break
    assert trafficgen_mtu != 0

    # use the smaller mtu between dut and trafficgen
    if "mtu" in settings.config:
        mtu = min(int(settings.config["mtu"]), dut_mtu, trafficgen_mtu)
    else:
        mtu = min(dut_mtu, trafficgen_mtu)

    assert set_mtu(trafficgen, trafficgen_pf, dut, pf, 0, mtu, testdata)

    steps = [f"ip link set {pf}v0 up", f"ip add add {dut_ip}/24 dev {pf}v0"]
    execute_and_assert(dut, steps, 0, 0.1)

    vf0_mac = get_vf_mac(dut, pf, 0)
    trafficgen_ip = testdata.trafficgen_ip
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

    ping_cmd = f"ping -W 1 -c 1 -s {mtu-28} -M do {trafficgen_ip}"
    assert execute_until_timeout(dut, ping_cmd)
