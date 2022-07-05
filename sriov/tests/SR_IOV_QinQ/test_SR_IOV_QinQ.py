import time
from sriov.common.utils import *

def test_SR_IOV_QinQ(dut, trafficgen, settings, testdata):
    dut_ip = testdata['dut_ip']
    outside_tag = 10
    inside_tag = 20
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
        
    steps = [
        f"ip link set {pf} vf 0 vlan {outside_tag} proto 802.1ad",
        f"ip link add link {pf}v0 name {pf}v0.{inside_tag} type vlan id {inside_tag}",
        f"ip link set {pf}v0.{inside_tag} up",
        f"ip add add {dut_ip}/24 dev {pf}v0.{inside_tag}",
        ]
    for step in steps:
        print(step)
        code, out, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    trafficgen_ip = testdata['trafficgen_ip']
    tmux_session = testdata['tmux_session_name']
    tmux_cmd = f"timeout 3 nping --dest-mac {trafficgen_mac} {trafficgen_ip}"
    print(tmux_cmd)
    start_tmux(dut, tmux_session, tmux_cmd)
    tgen_cmd = f"timeout 3 tcpdump -i {trafficgen_pf} -c 1 vlan {outside_tag} and vlan {inside_tag}"
    print(tgen_cmd)
    code, out, err = trafficgen.execute(tgen_cmd)
    stop_tmux(dut, tmux_session)
    assert code == 0, err