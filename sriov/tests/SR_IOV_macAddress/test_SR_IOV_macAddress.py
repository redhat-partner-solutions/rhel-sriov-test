import time
from sriov.common.utils import *

def test_SR_IOV_macAddress(dut, trafficgen, settings):
    trafficgen_ip = "101.1.1.1"
    dut_ip = "101.1.1.2"
    vf0_mac = "aa:bb:cc:dd:ee:00"
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
    trafficgen.execute("arp -s {} {}".format(dut_ip, vf0_mac))
    trafficgen.execute("ip address add {}/24 dev {}".format(trafficgen_ip, trafficgen_pf))
    code, out, err = trafficgen.execute("ping -W 1 -c 1 {}".format(dut_ip))
    assert code == 0, err

        
