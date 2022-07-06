from docutils import SettingsSpec
import pytest
import os
import logging
from sriov.common.exec import ShellHandler
from sriov.common.config import Config

from sriov.common.utils import *

LOGGER = logging.getLogger(__name__)

# Adjust the execution_number parameter for desired amount of repeated tests (or to 100 for actual testing)
@pytest.mark.parametrize('execution_number', range(1))
def test_SRIOVMultipleVFCreationwithMTU(dut, settings, testdata, execution_number):
    pf = list(testdata['pfs'].keys())[0] 

    steps = ["echo 1 > " + testdata['pf_net_paths'][pf] + "/sriov_numvfs",
             "ip link set " + testdata['pfs'][pf]['name'] + " vf 0 mac " + testdata['dut_mac'],
             "ip link set " + testdata['pfs'][pf]['name'] + " vf 0 spoof on",
             "ip link set " + testdata['pfs'][pf]['name'] + " vf 0 trust on",
             "ip link set " + testdata['pfs'][pf]['name'] + " vf 0 max_tx_rate 10",
             "ip link set " + testdata['pfs'][pf]['name'] + " vf 0 vlan 10 qos 5"
            ]
    for step in steps:
        code, out, err = dut.execute(step)
        assert code == 0, step

    vf = list(testdata['vfs'].keys())[0]
    vf_pci = testdata['vfs'][vf]['pci']
    assert bind_driver(dut, vf_pci, "vfio-pci")

    vf_mac = get_vf_mac(dut, testdata['pfs'][pf]['name'], 0)
    assert vf_mac == testdata['dut_mac']

