import pytest
import time
from sriov.common.utils import *


def stop_testpmd_in_tmux(dut, tmux_session):
    dut.execute(f"tmux send-keys -t {tmux_session} 'quit' ENTER")
    time.sleep(1)
    stop_tmux(dut, tmux_session)


@pytest.mark.parametrize('spoof', ("on", "off"))
@pytest.mark.parametrize('trust', ("on", "off"))
@pytest.mark.parametrize('qos', (True, False))
@pytest.mark.parametrize('vlan', (True, False))
@pytest.mark.parametrize('max_tx_rate', (True, False))
def test_SR_IOV_InterVF_DPDK(dut, settings, testdata, spoof,
                        trust, qos, vlan, max_tx_rate):
    """ Test and ensure that VFs bound to DPDK driver can communicate with VF on the same PF

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
    set_pipefail(dut)

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    mac_prefix = "aa:bb:cc:dd:ee:0"
    ip_prefix = "100.1.1.1"
    steps = [
        f"echo 0 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"echo 2 > /sys/class/net/{pf}/device/sriov_numvfs",
    ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(1)
    
    steps = [] 
    for i in range(2):
        steps.extend([
            f"ip link set {pf} vf {i} mac {mac_prefix}{i}",
            f"ip link set {pf} vf {i} spoof {spoof}",
            f"ip link set {pf} vf {i} trust {trust}",
        ])
        if vlan:
            qos_str = f"qos {testdata['qos']}" if qos else ""
            steps.append(
                f"ip link set {pf} vf {i} vlan {testdata['vlan']} {qos_str}")
        if max_tx_rate:
            steps.append(
                f"ip link set {pf} vf {i} max_tx_rate {testdata['max_tx_rate']}")
        
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    # bind VF0 to vfio-pci
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, vf_pci, "vfio-pci")

    # start first instance testpmd in echo mode
    dpdk_img = settings.config["dpdk_img"]
    cpus = settings.config["dut"]["pmd_cpus"]
    tmux_cmd = "podman run -it --rm --privileged "\
        "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules "\
        "--cpuset-cpus {} {} dpdk-testpmd -l {} "\
        "-n 4 -a {} "\
        "-- --nb-cores=2 --forward=icmpecho".format(cpus,dpdk_img,cpus,vf_pci)
    print(tmux_cmd)
    tmux_session = testdata['tmux_session_name']
    start_tmux(dut, tmux_session, tmux_cmd)
    
    # make sure tmux testpmd session has started
    for i in range(15):
        time.sleep(1)
        code, out, err = dut.execute(f"tmux capture-pane -pt {tmux_session}")
        started = False
        for line in out:
            if line.startswith("Press enter to exit"):
                started = True
                break
        if started:
            print("tmux: testpmd started")
            break

    vf_1_mac = get_vf_mac(dut, pf, 0)
    steps = [
        f"ip addr add {ip_prefix}1/24 dev {pf}v1",
        f"ip link set {pf}v1 up",
        f"arp -s {ip_prefix}0 {vf_1_mac}",
        f"ping -W 1 -c 1 {ip_prefix}0",
        f"arp -d {ip_prefix}0",
        f"ip addr del {ip_prefix}1/24 dev {pf}v1"
    ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        if code != 0:
            stop_testpmd_in_tmux(dut, tmux_session)
            assert False, err
        time.sleep(0.1)
    stop_testpmd_in_tmux(dut, tmux_session)
