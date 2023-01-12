from sriov.common.utils import (
    execute_and_assert,
    create_vfs,
    set_pipefail,
    get_pci_address,
    bind_driver,
)


# Use pytest --iteration to adjust the execution_number parameter for desired amount
# of repeated tests
def test_SRIOVMultipleVFCreationwithMACDPDK(dut, settings, testdata, execution_number):
    """Test and ensure that VFs provision with MTU functions as intended

    Args:
        dut:              ssh connection obj
        settings:         settings obj
        testdata:         testdata obj
        execution_number: execution_number parameter
    """
    pf = list(testdata.pfs.keys())[0]
    base_mac = "0x0000000000"

    assert set_pipefail(dut)

    # Create the maximum number of VFs allowed
    max_vfs_cmd = ["cat " + testdata.pf_net_paths[pf] + "/sriov_totalvfs"]
    outs, errs = execute_and_assert(dut, max_vfs_cmd, 0)
    max_vfs = outs[0][0].strip()
    assert create_vfs(dut, testdata.pfs[pf]["name"], int(max_vfs))

    # Set the MAC address for each VF, bind each VF to vfio-pci
    for i in range(int(max_vfs)):
        base_mac = "{:012X}".format(int(base_mac, 16) + 1)
        new_mac = ":".join(
            base_mac[i] + base_mac[i + 1] for i in range(0, len(base_mac), 2)
        )
        steps = [
            "ip link set "
            + testdata.pfs[pf]["name"]
            + " vf "
            + str(i)
            + " mac "
            + new_mac
        ]
        execute_and_assert(dut, steps, 0)

        vf_pci = get_pci_address(dut, testdata.pfs[pf]["name"] + "v" + str(i))
        assert bind_driver(dut, vf_pci, "vfio-pci", 1)
