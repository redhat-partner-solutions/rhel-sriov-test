from docutils import SettingsSpec
import pytest
import os
import logging
from sriov.common.exec import ShellHandler
from sriov.common.config import Config

from pytest_html import extras
from sriov.common.utils import *

LOGGER = logging.getLogger(__name__)

@pytest.mark.parametrize('execution_number', range(1))
def test_SRIOVMultipleVFCreationwithMTU(dut, settings, testdata, execution_number):
    for pf in testdata['pfs']:
        base_mac = "0x0000000000"

        max_vfs_cmd = "cat " + testdata['pf_net_paths'][pf] + "/sriov_totalvfs"
        code, out, err = dut.execute(max_vfs_cmd)
        assert code == 0
        max_vfs = out[0].strip()
    
        set_vfs = "echo " + max_vfs + " > " + testdata['pf_net_paths'][pf] + "/sriov_numvfs"
        code, out, err = dut.execute(set_vfs)
        assert code == 0

        code, out, err = dut.execute('sleep 2')
        assert code == 0
        
        check_vfs_created = vfs_created(dut, testdata['pfs'][pf]['name'], max_vfs)
        assert check_vfs_created == True

        check_vfs = "ip -d link show " + testdata['pfs'][pf]['name']
        code, out, err = dut.execute(check_vfs)
        assert code == 0
        for out_slice in out:
            assert "00:00:00:00:00:00" not in out_slice
    
        split_out = out[1].split()
        max_mtu = split_out[split_out.index("maxmtu") + 1]

        set_max_mtu = "ip link set " + testdata['pfs'][pf]['name'] + " mtu " + max_mtu
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
                code, out, err = dut.execute(step)
                assert code == 0, step

        set_mtu = "ip link set " + testdata['pfs'][pf]['name'] + " mtu 1500"
        code, out, err = dut.execute(set_mtu)
        assert code == 0
