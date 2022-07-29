import pytest
import time
from sriov.common.utils import *


@pytest.mark.parametrize('spoof', ("on", "off"))
@pytest.mark.parametrize('trust', ("on", "off"))
@pytest.mark.parametrize('qos', (True, False))
@pytest.mark.parametrize('vlan', (True, False))
@pytest.mark.parametrize('max_tx_rate', (True, False))
def test_SR_IOV_Permutation(dut, trafficgen, settings, testdata, spoof, 
                                trust, qos, vlan, max_tx_rate):
    """ Test VFs function with various properties

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
    set_pipefail(dut)

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {testdata['dut_mac']}",
        f"ip link set {pf} vf 0 spoof {spoof}",
        f"ip link set {pf} vf 0 trust {trust}",
        ]
    if vlan:
        qos_str = f"qos {testdata['qos']}" if qos else ""
        steps.append(f"ip link set {pf} vf 0 vlan {testdata['vlan']} {qos_str}")
    if max_tx_rate:
        steps.append(f"ip link set {pf} vf 0 max_tx_rate {testdata['max_tx_rate']}")
    steps.append(f"ip addr add {testdata['dut_ip']}/24 dev {pf}v0")
    steps.append(f"ip link set {pf}v0 up")
    
    create_vfs(dut, pf, 1)

    execute_and_assert(dut, steps, 0, 0.1)
    
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_vlan = testdata['vlan'] if vlan else 0
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan) 
    config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, testdata['trafficgen_ip'])
    add_arp_entry(trafficgen, testdata['dut_ip'], testdata['dut_mac'])
    cmd = ["ping -W 1 -c 1 {}".format(testdata['dut_ip'])]
    execute_and_assert(trafficgen, cmd, 0)
    rm_arp_entry(trafficgen, testdata['trafficgen_ip'])
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
