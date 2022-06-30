import pytest
import logging
from sriov.common.exec import ShellHandler
from sriov.common.utils import *


def test_SR_IOV_macAddress_DPDK(dut, trafficgen, settings):
    vf0_mac = "aa:bb:cc:dd:ee:00"
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
    
    trafficgen_ip = "101.1.1.1"
    dut_ip = "101.1.1.2"
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen.execute("arp -s {} {}".format(dut_ip, vf0_mac))
    trafficgen.execute("ip address add {}/24 dev {}".format(trafficgen_ip, trafficgen_pf))
    code, out, err = trafficgen.execute("ping -W 1 -c 1 {}".format(dut_ip))
    assert code == 0, err
    dut.stop_testpmd()

        
