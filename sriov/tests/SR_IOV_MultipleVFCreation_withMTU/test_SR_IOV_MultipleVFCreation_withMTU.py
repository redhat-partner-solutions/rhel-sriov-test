import pytest
from sriov.common.utils import *

# Use pytest --iteration to adjust the execution_number parameter for desired amount of repeated tests
def test_SRIOVMultipleVFCreationwithMTU(dut, settings, testdata, execution_number):
    """ Test and ensure that VFs provision with MTU functions as intended

    Args:
        dut:              ssh connection obj
        settings:         settings obj
        testdata:         testdata obj
        execution_number: execution_number parameter
    """
    pf = list(testdata['pfs'].keys())[0] 
    base_mac = "0x0000000000"
    
    set_pipefail(dut)

    max_vfs_cmd = "cat " + testdata['pf_net_paths'][pf] + "/sriov_totalvfs"
    print(max_vfs_cmd)
    code, out, err = dut.execute(max_vfs_cmd)
    assert code == 0
    max_vfs = out[0].strip()

    set_vfs = "echo " + max_vfs + " > " + testdata['pf_net_paths'][pf] + "/sriov_numvfs"
    print(set_vfs)
    code, out, err = dut.execute(set_vfs)
    assert code == 0

    check_vfs_created = vfs_created(dut, testdata['pfs'][pf]['name'], int(max_vfs))
    assert check_vfs_created == True

    check_no_zero_macs_pf = no_zero_macs_pf(dut, testdata['pfs'][pf]['name'])
    assert check_no_zero_macs_pf == True

    check_no_zero_macs_vf = no_zero_macs_vf(dut, testdata['pfs'][pf]['name'], int(max_vfs))
    assert check_no_zero_macs_vf == True

    check_mtu = "ip -d link show " + testdata['pfs'][pf]['name']
    print(check_mtu)
    code, out, err = dut.execute(check_mtu)
    assert code == 0

    split_out = out[1].split()
    max_mtu = split_out[split_out.index("maxmtu") + 1]

    set_max_mtu = "ip link set " + testdata['pfs'][pf]['name'] + " mtu " + max_mtu
    print(set_max_mtu)
    code, out, err = dut.execute(set_max_mtu)
    assert code == 0

    for i in range(int(max_vfs)):
        # Reference for incrementing mac addresses: https://stackoverflow.com/a/62210098
        base_mac = "{:012X}".format(int(base_mac, 16) + 1)
        new_mac = ":".join(base_mac[i]+base_mac[i+1] for i in range(0, len(base_mac), 2))
        steps = ["ip link set " + testdata['pfs'][pf]['name'] + " vf " + str(i) + " mac " + new_mac,
                 "sleep 0.5",
                 "ip link set " + testdata['pfs'][pf]['name'] + "v" + str(i) + " mtu " + max_mtu
                ]
        for step in steps:
            print(step)
            code, out, err = dut.execute(step)
            assert code == 0, step

    set_mtu = "ip link set " + testdata['pfs'][pf]['name'] + " mtu 1500"
    print(set_mtu)
    code, out, err = dut.execute(set_mtu)
    assert code == 0
