from time import sleep
from sriov.common.utils import (
    execute_and_assert,
)


class Bond:
    def __init__(self, mode):
        self.bond_mode = mode


def validate_bond (
    dut, trafficgen, settings, testdata, bond_mode
):
    pf1 = settings.config["dut"]["interface"]["pf1"]["name"]
    trafficgen_pf1 = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_pf2 = settings.config["trafficgen"]["interface"]["pf2"]["name"]
    fwd_mac = testdata.trafficgen_spoof_mac
    tcpdump_cmd = f"timeout 3 tcpdump -i {trafficgen_pf1} -c 1 ether dst {fwd_mac}"
    trafficgen.log_str(tcpdump_cmd)
    code, out, err = trafficgen.execute(tcpdump_cmd)
    assert code == 0, err

    if bond_mode == 1:
        link_down_cmd = f"ip link set {pf1} vf 0 state disable"
        execute_and_assert(dut, [link_down_cmd], 0)
        sleep(3)
    tcpdump_cmd = f"timeout 3 tcpdump -i {trafficgen_pf2} -c 1 ether dst {fwd_mac}"
    trafficgen.log_str(tcpdump_cmd)
    code, out, err = trafficgen.execute(tcpdump_cmd)
    assert code == 0, err

    if bond_mode == 1:
        link_up_cmd = f"ip link set {pf1} vf 0 state enable"
        execute_and_assert(dut, [link_up_cmd], 0)
        sleep(3)
        tcpdump_cmd = f"timeout 3 tcpdump -i {trafficgen_pf1} -c 1 ether dst {fwd_mac}"
        trafficgen.log_str(tcpdump_cmd)
        code, out, err = trafficgen.execute(tcpdump_cmd)
        assert code == 0