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
    """ Test VFs function when bound to the DPDK driver with various properties

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
    # For some reason, if these steps are executed line by line over ssh session
    # the mac address for the VF may not get set
    # If all these steps are put in a script and run the script over the ssh session,
    # then it is much better
    # this is only needed for DPDK case
    set_pipefail(dut)

    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    assert create_vfs(dut, pf, 1)
    
    assert set_vf_mac(dut, pf, 0, testdata['dut_mac'] )
    
    steps = [
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
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, pci, "vfio-pci")

    assert verify_vf_address(dut, pf, 0, testdata['dut_mac'])
    
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
    
