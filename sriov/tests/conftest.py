import pytest
import os
from sriov.common.exec import ShellHandler
from sriov.common.config import Config
from pytest_html import extras

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

def reset_command(dut, testdata):
    for pf in testdata['pf_net_paths']:
        clear_vfs = "echo 0 > " + testdata['pf_net_paths'][pf] + "/sriov_numvfs"
        code, out, err = dut.execute(clear_vfs, 60)
        assert code == 0

@pytest.fixture
def trafficgen(settings):
    host = settings.config["trafficgen"]["host"]
    user = settings.config["trafficgen"]["username"]
    password = settings.config["trafficgen"]["password"]
    return ShellHandler(host, user, password)

@pytest.fixture(autouse=True)
def _cleanup(dut, testdata):
    reset_command(dut, testdata)
    yield
    dut.stop_testpmd()
    reset_command(dut, testdata)

@pytest.fixture(autouse=True)
def _report_extras(extra, request):
    #extra.append(extras.json({"test": "test string"}))
    #print(request.node.name)
    # This is assuming report is in the same directory as the test and README.
    lines = []
    with open('README.md') as f:
        lines = f.readlines()
    f.close()
    
    case_name = ''
    for line in lines: 
        case_index = line.find('Case:')
        if case_index != -1:
            case_name = (line[case_index + 6:]).strip()
            break
    
    test_dir = os.path.dirname(request.module.__file__).split(os.sep)[-1]
    link = 'https://github.com/redhat-partner-solutions/intel-sriov-test/tree/extras_uuid/sriov/tests/' + test_dir + '/README.md'

    #extra.append(extras.html('<p>Link to the README: <a href="README.md">' + case_name + ' Documentation</a></p>'))
    extra.append(extras.html('<p>Link to the README: <a href="' + link + '">' + case_name + ' Documentation</a></p>'))
    extra.append(extras.json({"test case": case_name, "module": os.path.dirname(request.module.__file__)}))

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
                    '/sys/class/net/' + settings.config['dut']['interface'][interface]['name'] + '/device'
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
