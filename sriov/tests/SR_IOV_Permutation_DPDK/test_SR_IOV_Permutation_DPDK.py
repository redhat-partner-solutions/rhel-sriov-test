import pytest
import time
from sriov.common.utils import *


@pytest.mark.parametrize('spoof', ("on", "off"))
@pytest.mark.parametrize('trust', ("on", "off"))
@pytest.mark.parametrize('qos', (True, False))
@pytest.mark.parametrize('vlan', (True, False))
@pytest.mark.parametrize('max_tx_rate', (True, False))
def test_SR_IOV_Permutation_DPDK(dut, trafficgen, settings, testdata, spoof, 
                                trust, qos, vlan, max_tx_rate):
    # For some reason, if these steps are executed line by line over ssh session
    # the mac address for the VF may not get set
    # If all these steps are put in a script and run the script over the ssh session,
    # then it is much better
    # this is only needed for DPDK case
    set_pipefail(dut)

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    dut.execute("> steps.sh")
    steps = [
        f"echo 0 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"echo 1 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"ip link set {pf} vf 0 mac {testdata['dut_mac']}",
        f"ip link set {pf} vf 0 spoof {spoof}",
        f"ip link set {pf} vf 0 trust {trust}",
        ]
    if vlan:
        qos_str = f"qos {testdata['qos']}" if qos else ""
        steps.append(f"ip link set {pf} vf 0 vlan {testdata['vlan']} {qos_str}")
    if max_tx_rate:
        steps.append(f"ip link set {pf} vf 0 max_tx_rate {testdata['max_tx_rate']}")

    for step in steps:
        print(step)
        code, out, err = dut.execute(f"echo '{step}' >> steps.sh")
        assert code == 0, err
        #time.sleep(1)
    code, out, err = dut.execute("sh steps.sh")
    assert code == 0, err
    
    pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, pci, "vfio-pci")

    vf0_mac = get_vf_mac(dut, pf, 0)
    assert vf0_mac == testdata['dut_mac']
    
    dut.start_testpmd(testdata['podman_cmd'])
    assert dut.testpmd_active()
    
    steps = [
        "set fwd icmpecho",
        "start"
        ]
    for step in steps:
        print(step)
        code = dut.testpmd_cmd(step)
        assert code == 0
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_vlan = testdata['vlan'] if vlan else 0
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan) 
    config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, testdata['trafficgen_ip'])
    add_arp_entry(trafficgen, testdata['dut_ip'], testdata['dut_mac'])
    code, out, err = trafficgen.execute("ping -W 1 -c 1 {}".format(testdata['dut_ip']))
    rm_arp_entry(trafficgen, testdata['trafficgen_ip'])
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
    assert code == 0, err
    
