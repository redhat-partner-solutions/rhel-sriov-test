# UUID: 67e90840-5f2f-4423-a80d-828e99d43e55
from sriov.common.utils import create_vfs, execute_and_assert, verify_vf_address


def test_SR_IOV_macAddressDuplicate(dut, settings):
    """Test and ensure that duplicate mac address across VFs on the same PF is
       permitted

    Args:
        dut:      ssh connection obj
        settings: settings obj
    """

    mac_1 = "aa:bb:cc:dd:ee:11"
    mac_2 = "aa:bb:cc:dd:ee:22"
    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    # create 2 VFs
    create_vfs(dut, pf, 2)

    # assign mac addresses
    steps = [
        f"ip link set {pf} vf 0 mac {mac_1}",
        f"ip link set {pf} vf 1 mac {mac_2}",
    ]
    execute_and_assert(dut, steps, 0)

    # check if vf 0 mac address is equal to mac_1
    assert verify_vf_address(dut, pf, 0, mac_1)

    # check if vf 1 mac address is equal to mac_2
    assert verify_vf_address(dut, pf, 1, mac_2)

    # swap mac addresses between VFs
    steps = [
        f"ip link set {pf} vf 0 mac {mac_2}",
        f"ip link set {pf} vf 1 mac {mac_1}",
    ]
    execute_and_assert(dut, steps, 0, 1)

    # check if vf 0 mac address is equal to mac_2
    assert verify_vf_address(dut, pf, 0, mac_2)

    # check if vf 1 mac address is equal to mac_1
    assert verify_vf_address(dut, pf, 1, mac_1)
