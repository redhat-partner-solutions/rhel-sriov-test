import pytest
import os
import time
from sriov.common.exec import ShellHandler
from sriov.common.config import Config
from pytest_html import extras


def get_settings_obj():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = script_dir + "/config.yaml"
    return Config(config_file)


def get_ssh_obj(name):
    settings = get_settings_obj()
    host = settings.config[name]["host"]
    user = settings.config[name]["username"]
    password = settings.config[name]["password"]
    return ShellHandler(host, user, password)


@pytest.fixture
def settings():
    return get_settings_obj()


@pytest.fixture
def dut():
    return get_ssh_obj("dut")


def reset_command(dut, testdata):
    dut.execute("ip netns del ns0 2>/dev/null || true")
    dut.execute("ip netns del ns1 2>/dev/null || true")
    
    for pf in testdata['pf_net_paths']:
        clear_vfs = "echo 0 > " + \
            testdata['pf_net_paths'][pf] + "/sriov_numvfs"
        dut.execute(clear_vfs, 60)


@pytest.fixture
def trafficgen():
    return get_ssh_obj("trafficgen")


@pytest.fixture(autouse=True)
def _cleanup(dut, testdata):
    reset_command(dut, testdata)
    yield
    dut.stop_testpmd()
    reset_command(dut, testdata)


def pytest_configure(config):
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
    
    code, out, err = dut.execute("cat /sys/bus/pci/drivers/iavf/module/version")
    if code == 0:
        iavf_driver = out[0].strip()
    config._metadata["IAVF Driver"] = iavf_driver


def pytest_html_report_title(report):
    ''' modifying the title  of html report'''
    report.title = "SR-IOV Test Report"


@pytest.fixture(autouse=True)
def _report_extras(extra, request, settings, monkeypatch):
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
            extra.append(extras.json(
                {"test case": case_name, "test dir": os.path.dirname(request.module.__file__)}))
    except:
        return


@pytest.fixture
def testdata(settings):
    data = dict()
    data['vlan'] = 10
    data['dut_ip'] = "101.1.1.2"
    data['dut_mac'] = "aa:bb:cc:dd:ee:00"
    data['dut_spoof_mac'] = "aa:bb:cc:dd:ee:ff"
    data['trafficgen_ip'] = "101.1.1.1"
    data['qos'] = 5
    data['max_tx_rate'] = 10
    data['pfs'] = {}
    data['vfs'] = {}
    data['pf_net_paths'] = {}
    # NOTE: These should be done in a loop going forward
    for interface in settings.config['dut']['interface']:
        if 'pf' in interface:
            data['pfs'][interface] = settings.config['dut']['interface'][interface]
            data['pf_net_paths'][interface] = \
                '/sys/class/net/' + \
                settings.config['dut']['interface'][interface]['name'] + '/device'
        else:
            data['vfs'][interface] = settings.config['dut']['interface'][interface]
    data["tmux_session_name"] = "sriov_job"
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    dpdk_img = settings.config["dpdk_img"]
    cpus = settings.config["dut"]["pmd_cpus"]
    data['podman_cmd'] = "podman run -it --rm --privileged "\
        "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules "\
        "--cpuset-cpus {} {} dpdk-testpmd -l {} -n 4 -a {} "\
        "-- --nb-cores=2 -i".format(cpus, dpdk_img, cpus, vf_pci)
    return data

def pytest_addoption(parser):
    parser.addoption("--iteration", action="store", default="1",
                     help="Iterations for robustness test cases")

def pytest_generate_tests(metafunc):
    if "execution_number" in metafunc.fixturenames:
        if metafunc.config.getoption("iteration"):
            end = int(metafunc.config.option.iteration)
        else:
            end = 1
        metafunc.parametrize("execution_number", range(end))