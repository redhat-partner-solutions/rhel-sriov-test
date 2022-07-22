import time
import re
from sriov.common.utils import *


def test_SR_IOV_MTU(dut, trafficgen, settings, testdata):
    """ Test and ensure that VF MTU functions as intended

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """
    set_pipefail(dut)

    dut_ip = testdata['dut_ip']
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        f"echo 0 > /sys/class/net/{pf}/device/sriov_numvfs",
        f"echo 1 > /sys/class/net/{pf}/device/sriov_numvfs",
    ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(1)

    # command to get the maxmtu from the DUT
    cmd = f"ip -d link list {pf}"
    print(cmd)
    code, out, err = dut.execute(cmd)
    assert code == 0
    dut_mtu = 0
    for line in out:
        match = re.search(r'maxmtu (\d+)', line)
        if match is not None:
            dut_mtu = int(match.group(1))
            break
    assert dut_mtu != 0
    
    # get trafficgen maxmtu
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mtu = 0
    code, out, err = trafficgen.execute(f"ip -d link list {trafficgen_pf}")
    assert code == 0
    for line in out:
        match = re.search(r'maxmtu (\d+)', line)
        if match is not None:
            trafficgen_mtu = int(match.group(1))
            break
    assert trafficgen_mtu != 0
    
    # use the smaller mtu between dut and trafficgen
    mtu = min(dut_mtu, trafficgen_mtu)
    
    trafficgen.execute(f"ip link set {trafficgen_pf} mtu {mtu}")
    steps = [
        f"ip link set {pf} mtu {mtu}",
        f"ip link set {pf}v0 mtu {mtu}",
        f"ip link set {pf}v0 up",
        f"ip add add {dut_ip}/24 dev {pf}v0"
    ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    vf0_mac = get_vf_mac(dut, pf, 0)
    trafficgen_ip = testdata['trafficgen_ip']
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    trafficgen_vlan = 0
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
    config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, trafficgen_ip)
    add_arp_entry(trafficgen, dut_ip, vf0_mac)
    add_arp_entry(dut, trafficgen_ip, trafficgen_mac)

    time.sleep(1)
    ping_cmd = f"ping -W 1 -c 1 -s {mtu-28} -M do {trafficgen_ip}"
    print(ping_cmd)
    code, out, err = dut.execute(ping_cmd)
    print(code,out,err)

    # recover the system before the final assert
    rm_arp_entry(trafficgen, dut_ip)
    clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
    rm_arp_entry(dut, trafficgen_ip)
    trafficgen.execute(f"ip link set {trafficgen_pf} mtu 1500")
    dut.execute(f"echo 0 > /sys/class/net/{pf}/device/sriov_numvfs")
    dut.execute(f"ip link set {pf} mtu 1500")
    
    assert code == 0, err
