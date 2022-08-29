import pytest
from time import sleep
from sriov.common.utils import (
    create_vfs,
    set_vf_mac,
    execute_and_assert,
    bind_driver,
    prepare_ping_test,
    get_pci_address,
    start_tmux,
    wait_tmux_testpmd_ready,
    stop_tmux,
    stop_testpmd_in_tmux,
)


@pytest.mark.parametrize("mode", (0, 1))
def test_SR_IOV_Permutation_DPDK(
    dut, trafficgen, settings, testdata, mode
):
    """Test VFs function when bound to the DPDK driver with various properties

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

    pci_pf1_vf0 = get_pci_address(dut, pf1+"v0")
    assert bind_driver(dut, pci_pf1_vf0, "vfio-pci")
    pci_pf1_vf1 = get_pci_address(dut, pf1+"v1")
    assert bind_driver(dut, pci_pf1_vf1, "vfio-pci")
    pci_pf2_vf0 = get_pci_address(dut, pf2+"v0")
    assert bind_driver(dut, pci_pf2_vf0, "vfio-pci") 
    rx_port_num = 1 if pci_pf1_vf1 < pci_pf2_vf0 else 2
    fwd_mac = "dd:cc:bb:aa:33:00"
    dpdk_img = settings.config["dpdk_img"]
    cpus = settings.config["dut"]["pmd_cpus"]
    podman_cmd = f"""podman run -it --rm --privileged \
        -v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules \
        --cpuset-cpus {cpus} {dpdk_img} \
        dpdk-testpmd -l {cpus} -n 4 \
        -a {pci_pf1_vf0} -a {pci_pf1_vf1} -a {pci_pf2_vf0} \
        --vdev net_bonding_bond_test,mode=1,slave={pci_pf1_vf0},slave={pci_pf2_vf0},primary={pci_pf1_vf0} \
        -- --forward-mode=mac --portlist {rx_port_num},3 \
        --eth-peer 3,{fwd_mac}"""
    dut.log_str(podman_cmd)
    testpmd_tmux_session = testdata.tmux_session_name
    assert start_tmux(dut, testpmd_tmux_session, podman_cmd)
    assert wait_tmux_testpmd_ready(dut, testpmd_tmux_session, 10)

    trafficgen_pf1 = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_pf2 = settings.config["trafficgen"]["interface"]["pf2"]["name"]
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
    
    tcpdump_cmd = f"timeout 3 tcpdump -i {trafficgen_pf1} -c 1 ether host {fwd_mac}"
    code_primary_link, out, err = trafficgen.execute(tcpdump_cmd)

    link_down_cmd = f"ip link set {pf1} vf 0 state disable"
    execute_and_assert(dut, [link_down_cmd], 0)
    
    tcpdump_cmd = f"timeout 3 tcpdump -i {trafficgen_pf2} -c 1 ether host {fwd_mac}"
    code_backup_link, out, err = trafficgen.execute(tcpdump_cmd)
    
    stop_tmux(trafficgen, ping_tmux_session)
    stop_testpmd_in_tmux(dut, testpmd_tmux_session)
    assert code_primary_link == 0
    assert code_backup_link == 0


    
