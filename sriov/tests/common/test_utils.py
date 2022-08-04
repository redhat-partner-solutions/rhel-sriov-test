import time
from sriov.common.utils import (
    bind_driver,
    start_tmux,
    stop_tmux,
    execute_and_assert,
    get_intf_mac,
    get_pci_address,
)


def create_vf(dut, pf_name):
    steps = [
        f"echo 0 > /sys/class/net/{pf_name}/device/sriov_numvfs",
        f"echo 1 > /sys/class/net/{pf_name}/device/sriov_numvfs",
    ]
    for step in steps:
        code, _, err = dut.execute(step)
        assert code == 0, err
        time.sleep(0.1)


def test_get_pci_address(dut, settings):
    pf_pci = settings.config["dut"]["interface"]["pf1"]["pci"]
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    assert pf_pci == get_pci_address(dut, pf_name)

    create_vf(dut, pf_name)
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    vf_name = settings.config["dut"]["interface"]["vf1"]["name"]
    assert vf_pci == get_pci_address(dut, vf_name)


def test_bind_driver(dut, settings):
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    create_vf(dut, pf_name)
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, vf_pci, "vfio-pci")


def test_tmux(dut, testdata):
    name = testdata["tmux_session_name"]
    start_tmux(dut, name, "sleep 8")
    stop_tmux(dut, name)


def test_get_intf_mac(trafficgen, settings):
    mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    pf_name = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    assert mac == get_intf_mac(trafficgen, pf_name)


def test_set_pipefail(dut):
    test_cmd = "false | echo test"
    code, _, err = dut.execute(test_cmd)
    assert code != 0


def test_execute_and_assert(dut):
    invalid_cmds = ["invalid_command", "also_invalid"]
    out, err = execute_and_assert(dut, invalid_cmds, 127)

    valid_cmds = ["echo Hello", "ls"]
    out, err = execute_and_assert(dut, valid_cmds, 0)
    assert "Hello" in out[0][0]
