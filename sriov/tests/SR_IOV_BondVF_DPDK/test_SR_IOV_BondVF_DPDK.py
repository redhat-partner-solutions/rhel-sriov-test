import pytest
from time import sleep
from sriov.common.utils import (
    create_vfs,
    set_vf_mac,
    get_vf_mac,
    execute_and_assert,
    bind_driver,
    prepare_ping_test,
    get_pci_address,
    start_tmux,
    wait_tmux_testpmd_ready,
    stop_tmux,
    stop_testpmd_in_tmux,
    setup_hugepages,
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
    # Setup hugepages for 1 testpmd instance
    setup_hugepages(dut, 1)

    mode = request.param["mode"]
    explicit_mac = request.param["mac"]
    if mode == 1 and explicit_mac:
        pytest.xfail(
            "Expected failure - mode 1 with explicit bond mac. That should work."
        )
    pf1 = settings.config["dut"]["interface"]["pf1"]["name"]
    assert create_vfs(dut, pf1, 2)
    pf2 = settings.config["dut"]["interface"]["pf2"]["name"]
    assert create_vfs(dut, pf2, 1)

    sleep(1)
    assert set_vf_mac(dut, pf1, 1, testdata.dut_mac)
    sleep(1)

    steps = [
        f"ip link set {pf1} vf 0 trust on",
        f"ip link set {pf1} vf 1 trust on",
        f"ip link set {pf2} vf 0 trust on",
    ]

    execute_and_assert(dut, steps, 0, 0.1)

    pci_pf1_vf0 = get_pci_address(dut, pf1 + "v0")
    assert bind_driver(dut, pci_pf1_vf0, "vfio-pci")
    pci_pf1_vf1 = get_pci_address(dut, pf1 + "v1")
    assert bind_driver(dut, pci_pf1_vf1, "vfio-pci")
    pci_pf2_vf0 = get_pci_address(dut, pf2 + "v0")
    assert bind_driver(dut, pci_pf2_vf0, "vfio-pci")

    if explicit_mac:
        bond_mac = testdata.dut_spoof_mac
    else:
        bond_mac = get_vf_mac(dut, pf1, 0)
    rx_port_num = 1 if pci_pf1_vf1 < pci_pf2_vf0 else 2
    fwd_mac = testdata.trafficgen_spoof_mac
    dpdk_img = settings.config["dpdk_img"]
    cpus = settings.config["dut"]["pmd_cpus"]

    vdev_str = (
        f"net_bonding_bond_test,mode={mode},"
        f"slave={pci_pf1_vf0},slave={pci_pf2_vf0},"
        f"primary={pci_pf1_vf0}"
    )
    if explicit_mac:
        vdev_str = f"{vdev_str},mac={bond_mac}"

    # The bond container command is specialized, so the testdata based commands
    # are not used.
    container_cmd = (
        f"{settings.config['container_manager']} run -it --rm --privileged "
        "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules "
        f"--cpuset-cpus {cpus} {dpdk_img} "
        f"dpdk-testpmd -l {cpus} -n 4 "
        f"-a {pci_pf1_vf0} -a {pci_pf1_vf1} -a {pci_pf2_vf0} "
        f"--vdev {vdev_str} "
        f"-- --forward-mode=mac --portlist {rx_port_num},3 "
        f"--eth-peer 3,{fwd_mac}"
    )
    dut.log_str(container_cmd)
    testpmd_tmux_session = testdata.tmux_session_name
    assert start_tmux(dut, testpmd_tmux_session, container_cmd)
    assert wait_tmux_testpmd_ready(dut, testpmd_tmux_session, 10)
    yield Bond(mode, bond_mac)
    stop_testpmd_in_tmux(dut, testpmd_tmux_session)


@pytest.fixture
def trafficgen_setup(dut, trafficgen, settings, testdata):
    """trafficgen setup and teardown fixture

    Args:
        dut: dut ssh connection obj
        trafficgen: trafficgen ssh connection obj
        settings: setting obj
        testdata: testdata obj
    """
    trafficgen_pf1 = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_ip = testdata.trafficgen_ip
    dut_ip = testdata.dut_ip
    assert prepare_ping_test(
        trafficgen,
        trafficgen_pf1,
        0,
        trafficgen_ip,
        None,
        dut,
        dut_ip,
        testdata.dut_mac,
        testdata,
    )

    ping_cmd = f"ping -i 0.3 {dut_ip}"
    trafficgen.log_str(ping_cmd)
    ping_tmux_session = "dpdk_bonding_ping"
    assert start_tmux(trafficgen, ping_tmux_session, ping_cmd)
    yield
    stop_tmux(trafficgen, ping_tmux_session)


bond_setup_params = (
    {"mode": mode, "mac": mac} for mode in [0, 1] for mac in [False, True]
)


@pytest.mark.parametrize("dut_setup", bond_setup_params, indirect=True)
def test_SR_IOV_BondVF_DPDK(
    dut, trafficgen, settings, testdata, dut_setup, trafficgen_setup
):
    """Test and ensure that DPDK VF bonding (mode 0, 1) functions as intended

    Args:
        dut: ssh connection obj
        trafficgen: trafficgen obj
        settings: settings obj
        testdata: testdata obj
        dut_setup: dut setup and teardown fixture
        trafficgen_setup: trafficgen setup and teardown fixture
    """
    validate_bond(
        dut, trafficgen, settings, testdata, dut_setup.bond_mode, dut_setup.bond_mac
    )
