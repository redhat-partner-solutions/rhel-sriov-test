import os
import pytest
from pytest_html import extras
from sriov.common.config import Config
from sriov.common.configtestdata import ConfigTestData
from sriov.common.exec import ShellHandler
from sriov.common.utils import cleanup_after_ping, reset_mtu, set_pipefail
from typing import *

def get_settings_obj() -> Config:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = script_dir + "/config.yaml"
    return Config(config_file)


def get_ssh_obj(name: str) -> ShellHandler:
    settings = get_settings_obj()
    host = settings.config[name]["host"]
    user = settings.config[name]["username"]
    password = settings.config[name]["password"]
    return ShellHandler(host, user, password)

def get_testdata_obj(settings: Config) -> ConfigTestData:
    return ConfigTestData(settings)

@pytest.fixture
def settings() -> Config:
    return get_settings_obj()


@pytest.fixture
def dut() -> ShellHandler:
    return get_ssh_obj("dut")

@pytest.fixture
def testdata(settings: Config) -> ConfigTestData:
    return get_testdata_obj(settings)

def reset_command(dut: ShellHandler, testdata) -> None:
    dut.execute("ip netns del ns0 2>/dev/null || true")
    dut.execute("ip netns del ns1 2>/dev/null || true")
    
    for pf in testdata.pf_net_paths:
        clear_vfs = "echo 0 > " + \
            testdata.pf_net_paths[pf] + "/sriov_numvfs"
        dut.execute(clear_vfs, 60)


@pytest.fixture
def trafficgen() -> ShellHandler:
    return get_ssh_obj("trafficgen")

# Great idea from
# https://stackoverflow.com/questions/3806695/how-to-stop-all-tests-from-inside-a-test-or-setup-using-unittest
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    return rep


@pytest.fixture(autouse=True)
def _cleanup(dut: ShellHandler, trafficgen: ShellHandler, testdata, skipclean: bool, request) -> None:
    reset_command(dut, testdata)
    yield
    # For debug test failure purpose,
    # use --skipclean to stop the test immediately without cleaning
    if request.node.rep_call.failed and skipclean:
        pytest.exit("stop the test run without cleanup")
    dut.stop_testpmd()
    cleanup_after_ping(trafficgen, dut, testdata)
    reset_mtu(trafficgen, dut, testdata)
    reset_command(dut, testdata)


def pytest_configure(config: Config) -> None:
    dut = get_ssh_obj("dut")
    # Need to clear the terminal before the first command, there may be some
    # residual text from ssh
    code, out, err = dut.execute("clear")
    code, out, err = dut.execute("uname -r")
    dut_kernel_version = out[0].strip("\n") if code == 0 else "unknown"
    config._metadata["DUT Kernel"] = dut_kernel_version

    settings = get_settings_obj()
    dut_pf1_name = settings.config["dut"]["interface"]["pf1"]["name"]
    code, out, err = dut.execute(f"ethtool -i {dut_pf1_name}")
    driver = "unknown"
    version = "unknown"
    firmware = "unknown"
    iavf_driver = "unknown"
    if code == 0:
        for line in out:
            parts = line.split(" ")
            if parts[0] == "driver:":
                driver = parts[1]
            elif parts[0] == "version:":
                version = parts[1]
            elif parts[0] == "firmware-version:":
                firmware = parts[1]
    config._metadata["NIC Driver"] = f"{driver} {version}"
    config._metadata["NIC Firmware"] = firmware

    code, out, err = dut.execute(
        "cat /sys/bus/pci/drivers/iavf/module/version")
    if code == 0:
        iavf_driver = out[0].strip()
    config._metadata["IAVF Driver"] = iavf_driver


def pytest_html_report_title(report) -> None:
    ''' modifying the title  of html report'''
    report.title = "SR-IOV Test Report"


@pytest.fixture(autouse=True)
def _report_extras(extra, request, settings, monkeypatch) -> None:
    lines = []
    monkeypatch.chdir(request.fspath.dirname)

    try:
        # This is assuming the current working directory contains the test specification.
        with open(settings.config['tests_doc_file']) as f:
            lines = f.readlines()

        case_name = ''
        for line in lines:
            case_index = line.find(settings.config['tests_name_field'])
            if case_index != -1:
                case_name = (
                    line[case_index + len(settings.config['tests_name_field']):]).strip()
                break

        if case_name != '':
            test_dir = os.path.dirname(
                request.module.__file__).split(os.sep)[-1]
            link = settings.config['github_tests_path'] + '/' + \
                test_dir + '/' + settings.config['tests_doc_file']
            extra.append(extras.html('<p>Link to the test specification: <a href="' +
                                     link + '">' + case_name + ' Documentation</a></p>'))
    except:
        return

def pytest_addoption(parser) -> None:
    parser.addoption("--iteration", action="store", default="1",
                     help="Iterations for robustness test cases")
    parser.addoption("--skipclean", action="store_true", default=False,
                     help="Do not clean up when a test case fails")

def pytest_generate_tests(metafunc) -> None:
    if "execution_number" in metafunc.fixturenames:
        if metafunc.config.getoption("iteration"):
            end = int(metafunc.config.option.iteration)
        metafunc.parametrize("execution_number", range(end))


@pytest.fixture(scope='session')
def skipclean(request):
    return request.config.option.skipclean
