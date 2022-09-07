"""
This file is a collection of test steps that are not good canidate for common util
functions.

For example, common test steps that involve test case specific asserts and are shared
between multiple test cases may be good candidate for this file.
"""

from sriov.common.utils import (
    execute_and_assert,
    verify_vf_address,
)


class Bond:
    """This class is used by bond setup code to yield an object with bond info"""

    def __init__(self, mode, mac):
        self.bond_mode = mode
        self.bond_mac = mac


def validate_bond(
    dut, trafficgen, settings, testdata, bond_mode, bond_mac
):
    """A common collection of steps to validate kernel bond and DPDK bond

    Args:
        dut: ssh connection obj
        trafficgen: trafficgen obj
        settings: settings obj
        testdata: testdata obj
        bond_mod: bond mode, choice of [0, 1]
        bond_mac: mac address for bond interface
    """
    pf1 = settings.config["dut"]["interface"]["pf1"]["name"]
    pf2 = settings.config["dut"]["interface"]["pf2"]["name"]
    trafficgen_pf1 = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_pf2 = settings.config["trafficgen"]["interface"]["pf2"]["name"]
    fwd_mac = testdata.trafficgen_spoof_mac
    tcpdump_cmd = (
        f"timeout 3 tcpdump -i {trafficgen_pf1} -c 1 "
        f"ether src {bond_mac} and ether dst {fwd_mac}"
    )
    trafficgen.log_str(tcpdump_cmd)
    code, out, err = trafficgen.execute(tcpdump_cmd)
    assert code == 0, err

    if bond_mode == 1:
        # shut down the VF only if it is bond mode 1
        link_down_cmd = f"ip link set {pf1} vf 0 state disable"
        execute_and_assert(dut, [link_down_cmd], 0)
    assert verify_vf_address(dut, pf2, 0, bond_mac, interval=1)
    # traffic should switch over to the backup VF
    tcpdump_cmd = (
        f"timeout 3 tcpdump -i {trafficgen_pf2} -c 1 "
        f"ether src {bond_mac} and ether dst {fwd_mac}"
    )
    trafficgen.log_str(tcpdump_cmd)
    code, out, err = trafficgen.execute(tcpdump_cmd)
    assert code == 0, err

    if bond_mode == 1:
        # switch back only for bond mode 1
        link_up_cmd = f"ip link set {pf1} vf 0 state enable"
        execute_and_assert(dut, [link_up_cmd], 0)
        assert verify_vf_address(dut, pf1, 0, bond_mac, interval=1)
        tcpdump_cmd = (
            f"timeout 3 tcpdump -i {trafficgen_pf1} -c 1 "
            f"ether src {bond_mac} and ether dst {fwd_mac}"
        )
        trafficgen.log_str(tcpdump_cmd)
        code, out, err = trafficgen.execute(tcpdump_cmd)
        assert code == 0
