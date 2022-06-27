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