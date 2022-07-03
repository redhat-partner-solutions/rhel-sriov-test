import pytest
import logging
from sriov.common.exec import ShellHandler
from sriov.common.utils import *


def test_SR_IOV_macAddress_DPDK(dut, trafficgen, settings, testdata):
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_ip = testdata['trafficgen_ip']
    dut_ip = testdata['dut_ip']
    vf0_mac = testdata['dut_mac']
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        "echo 0 > /sys/class/net/{}/device/sriov_numvfs".format(pf),
        "echo 1 > /sys/class/net/{}/device/sriov_numvfs".format(pf),
        "ip link set {} vf 0 mac {}".format(pf, vf0_mac),      
        ]
    for step in steps:
        code, out, err = dut.execute(step)
        assert code == 0, err
    
    vf_pci = get_pci_address(dut, pf+"v0")
    assert bind_driver(dut, vf_pci, "vfio-pci")
    
    dpdk_img = settings.config["dpdk_img"]
    cpus = settings.config["dut"]["pmd_cpus"]
    podman_cmd = "podman run -it --rm --privileged "\
                 "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules "\
                 "--cpuset-cpus {} {} dpdk-testpmd -l {} -n 4 -a {} "\
                 "-- --nb-cores=2 -i".format(cpus, dpdk_img, cpus, vf_pci)
    print(podman_cmd)
    dut.start_testpmd(podman_cmd)
    assert dut.testpmd_active()
    
    steps = [
        "set fwd icmpecho",
        "start"
        ]
    for step in steps:
        code = dut.testpmd_cmd(step)
        assert code == 0

    trafficgen_vlan = 0    
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan) 
    config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, trafficgen_ip)
    add_arp_entry(trafficgen, dut_ip, vf0_mac)
    code, out, err = trafficgen.execute("ping -W 1 -c 1 {}".format(dut_ip))
    rm_arp_entry(trafficgen, trafficgen_ip)
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
    dut.stop_testpmd()
    assert code == 0, err


        
