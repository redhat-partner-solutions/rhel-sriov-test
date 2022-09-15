import pytest
from sriov.common.utils import (
    create_vfs,
    get_vf_mac,
    execute_and_assert,
    start_tmux,
    stop_tmux,
)
from sriov.common.macros import (
    Bond,
    validate_bond,
)


@pytest.fixture
def dut_setup(dut, settings, testdata, request) -> Bond:
    """dut setup and teardown fixture

    Args:
        dut: dut ssh connection obj
        settings: setting obj
        testdata: testdata obj
        request: request fixture
    """
    mode = request.param["mode"]
    explicit_mac = request.param["mac"]
    fwd_mac = testdata.trafficgen_spoof_mac
    fwd_ip = testdata.trafficgen_ip
    pf1 = settings.config["dut"]["interface"]["pf1"]["name"]
    assert create_vfs(dut, pf1, 1)
    pf2 = settings.config["dut"]["interface"]["pf2"]["name"]
    assert create_vfs(dut, pf2, 1)

    steps = [
        "modprobe bonding",
        f"ip link set {pf1} vf 0 trust on",
        f"ip link set {pf2} vf 0 trust on",
        f"ip link set {pf1}v0 down",
        f"ip link set {pf2}v0 down",
        "echo -bond0 > /sys/class/net/bonding_masters || true",
        "echo +bond0 > /sys/class/net/bonding_masters",
        "ip link set bond0 down",
    ]

    if explicit_mac:
        bond_mac = testdata.dut_spoof_mac
        steps.append(f"ip link set bond0 address {bond_mac}")
    else:
        bond_mac = get_vf_mac(dut, pf1, 0)

    steps.extend(
        [f"echo {mode} > /sys/class/net/bond0/bonding/mode",
         "echo 100 > /sys/class/net/bond0/bonding/miimon",
         f"echo +{pf1}v0 > /sys/class/net/bond0/bonding/slaves",
         f"echo +{pf2}v0 > /sys/class/net/bond0/bonding/slaves",
         ])

    if mode == 1:
        steps.append(f"echo {pf1}v0 > /sys/class/net/bond0/bonding/primary")

    steps.extend([
        "ip link set bond0 up",
        f"ip address add {testdata.dut_ip}/24 dev bond0",
        f"arp -s {fwd_ip} {fwd_mac}",
    ])

    execute_and_assert(dut, steps, 0, 0.1)

    ping_tmux_session = testdata.tmux_session_name
    ping_cmd = f"ping -i 0.3 {testdata.trafficgen_ip}"
    assert start_tmux(dut, ping_tmux_session, ping_cmd)
    yield Bond(mode, bond_mac)
    stop_tmux(dut, ping_tmux_session)
    steps = ["echo -bond0 > /sys/class/net/bonding_masters"]
    execute_and_assert(dut, steps, 0, 0.1)


bond_setup_params = ({"mode": mode, "mac": mac}
                     for mode in [0, 1]
                     for mac in [False, True]
                     )


@pytest.mark.parametrize('dut_setup', bond_setup_params, indirect=True)
def test_SR_IOV_BondVF(
    dut, trafficgen, settings, testdata, dut_setup
):
    """Test and ensure that Kernel VF bonding (mode 0, 1) functions as intended

    Args:
        dut: ssh connection obj
        trafficgen: trafficgen obj
        settings: settings obj
        testdata: testdata obj
        dut_setup: dut setup and teardown fixture
    """
    validate_bond(dut, trafficgen, settings, testdata,
                  dut_setup.bond_mode, dut_setup.bond_mac)
