import pytest
from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    get_nic_model,
    start_tmux,
    stop_tmux,
)


def test_SR_IOV_QinQ(dut, trafficgen, settings, testdata):
    """Test and ensure that QinQ on VF works with the kernel driver

    Args:
        dut:        ssh connection obj
        trafficgen: trafficgen obj
        settings:   settings obj
        testdata:   testdata obj
    """

    dut_ip = testdata.dut_ip
    outside_tag = testdata.vlan
    inside_tag = 20
    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    if "xxv710" in get_nic_model(dut, pf).lower():
        pytest.xfail("Expected failure - XXV710 NICs fail QinQ.")

    assert create_vfs(dut, pf, 1)

    steps = [
        f"ip link set {pf} vf 0 vlan {outside_tag} proto 802.1ad",
        f"ip link add link {pf}v0 name {pf}v0.{inside_tag} type vlan id {inside_tag}",
        f"ip link set {pf}v0.{inside_tag} up",
        f"ip add add {dut_ip}/24 dev {pf}v0.{inside_tag}",
    ]

    execute_and_assert(dut, steps, 0, 0.1)

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    trafficgen_ip = testdata.trafficgen_ip
    tmux_session = testdata.tmux_session_name
    tmux_cmd = f"timeout 3 nping --dest-mac {trafficgen_mac} {trafficgen_ip}"
    print(tmux_cmd)
    assert start_tmux(dut, tmux_session, tmux_cmd)
    tgen_cmd = f"timeout 3 tcpdump -i {trafficgen_pf} -c 1 \
        vlan {outside_tag} and vlan {inside_tag}"
    trafficgen.log_str(tgen_cmd)
    code, out, err = trafficgen.execute(tgen_cmd)
    assert stop_tmux(dut, tmux_session)
    assert code == 0, err
