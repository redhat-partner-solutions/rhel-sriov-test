from docutils import SettingsSpec
import pytest
from sriov.common.utils import *

def test_get_pci_address(dut, settings):
    pf_pci = settings.config["dut"]["interface"]["pf1"]["pci"]
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    assert pf_pci == get_pci_address(dut, pf_name)
    
def test_bind_driver(dut, settings):
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, vf_pci, "vfio-pci")