import pytest
import os
from sriov.common.exec import ShellHandler
from sriov.common.config import Config


@pytest.fixture
def settings():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = script_dir + "/config.yaml"
    return Config(config_file)

@pytest.fixture
def dut(settings):
    host = settings.config["dut"]["host"]
    user = settings.config["dut"]["username"]
    password = settings.config["dut"]["password"]
    return ShellHandler(host, user, password)

@pytest.fixture(autouse=True)
def initialization(dut, settings, pf_net_path):
    reset_command(dut, settings, pf_net_path)

@pytest.fixture()
def pf_name(settings):
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    return pf_name

@pytest.fixture()
def pf_net_path(settings, pf_name):
    pf_net_path = "/sys/class/net/"+ pf_name + '/device'
    return pf_net_path

@pytest.fixture
def reset_vfs(dut, settings, pf_net_path):
    yield
    reset_command(dut, settings, pf_net_path)

def reset_command(dut, settings, pf_net_path):
    clear_vfs = "echo 0 > " + pf_net_path + "/sriov_numvfs"
    code, out, err = dut.execute(clear_vfs, 60)
    assert code == 0
