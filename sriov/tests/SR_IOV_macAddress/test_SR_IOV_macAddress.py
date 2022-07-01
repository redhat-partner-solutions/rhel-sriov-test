import time
from sriov.common.utils import *

def test_SR_IOV_macAddress(dut, trafficgen, settings, testdata):
    trafficgen_ip = testdata['trafficgen_ip']
    dut_ip = testdata['dut_ip']
    vf0_mac = testdata['dut_mac']
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        "echo 0 > /sys/class/net/{}/device/sriov_numvfs".format(pf),
        "echo 1 > /sys/class/net/{}/device/sriov_numvfs".format(pf),
        "ip link set {}v0 down".format(pf),
        "ip link set {} vf 0 mac {}".format(pf, vf0_mac),
        "ip link set {}v0 up".format(pf),
        "ip add add {}/24 dev {}v0".format(dut_ip, pf) 
        ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_vlan = 0
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan) 
    config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, trafficgen_ip)
    add_arp_entry(trafficgen, dut_ip, vf0_mac)
    code, out, err = trafficgen.execute("ping -W 1 -c 1 {}".format(testdata['dut_ip']))
    rm_arp_entry(trafficgen, trafficgen_ip)
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
    assert code == 0, err

        
