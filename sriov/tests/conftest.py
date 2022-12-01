import git
import os
import pytest
from pytest_html import extras
import requests
from sriov.common.config import Config
from sriov.common.configtestdata import ConfigTestData
from sriov.common.exec import ShellHandler
from sriov.common.utils import cleanup_after_ping, reset_mtu, set_pipefail
import yaml


def get_settings_obj() -> Config:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = script_dir + "/config.yaml"
    testbed_file = script_dir + "/testbed.yaml"
    return Config(config_file, testbed_file)


def get_ssh_obj(name: str) -> ShellHandler:
    settings = get_settings_obj()
    host = settings.config[name]["host"]
    user = settings.config[name]["username"]
    if "password" in settings.config[name]:
        password = settings.config[name]["password"]
    else:
        password = None
    return ShellHandler(host, user, password, name)


def get_testdata_obj(settings: Config) -> ConfigTestData:
    return ConfigTestData(settings)


@pytest.fixture
def settings() -> Config:
    return get_settings_obj()


@pytest.fixture
def dut() -> ShellHandler:
    dut_obj = get_ssh_obj("dut")
    assert set_pipefail(dut_obj)
    return dut_obj


@pytest.fixture
def testdata(settings: Config) -> ConfigTestData:
    return get_testdata_obj(settings)


def reset_command(dut: ShellHandler, testdata) -> None:
    cmd_ns0 = "ip netns del ns0 2>/dev/null || true"
    cmd_ns1 = "ip netns del ns1 2>/dev/null || true"
    dut.log_str(cmd_ns0)
    dut.execute(cmd_ns0)
    dut.log_str(cmd_ns1)
    dut.execute(cmd_ns1)

    for pf in testdata.pf_net_paths:
        clear_vfs = "echo 0 > " + testdata.pf_net_paths[pf] + "/sriov_numvfs"
        dut.log_str(clear_vfs)
        dut.execute(clear_vfs, 60)


@pytest.fixture
def trafficgen() -> ShellHandler:
    trafficgen_obj = get_ssh_obj("trafficgen")
    assert set_pipefail(trafficgen_obj)
    return trafficgen_obj


# Great idea from
# https://stackoverflow.com/questions/3806695/how-to-stop-all-tests-from-inside-a-test-or-setup-using-unittest
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    return rep


@pytest.fixture(autouse=True)
def _cleanup(
    dut: ShellHandler, trafficgen: ShellHandler, testdata, skipclean: bool, request
) -> None:
    reset_command(dut, testdata)
    yield
    # For debug test failure purpose,
    # use --skipclean to stop the test immediately without cleaning
    try:
        if request.node.rep_call.failed and skipclean:
            pytest.exit("stop the test run without cleanup")
    except (AttributeError, NameError):
        # most likely request.node.rep_call not exist, continue normal cleanup
        pass
    dut.stop_testpmd()
    assert cleanup_after_ping(trafficgen, dut, testdata)
    assert reset_mtu(trafficgen, dut, testdata)
    reset_command(dut, testdata)


def pytest_configure(config: Config) -> None:
    dut = get_ssh_obj("dut")
    # Need to clear the terminal before the first command, there may be some
    # residual text from ssh
    cmd_clear = "clear"
    cmd_uname = "uname -r"
    dut.log_str(cmd_clear)
    code, out, err = dut.execute(cmd_clear)
    dut.log_str(cmd_uname)
    code, out, err = dut.execute(cmd_uname)
    dut_kernel_version = out[0].strip("\n") if code == 0 else "unknown"
    config._metadata["DUT Kernel"] = dut_kernel_version

    settings = get_settings_obj()
    dut_pf1_name = settings.config["dut"]["interface"]["pf1"]["name"]
    cmd_ethtool = f"ethtool -i {dut_pf1_name}"
    dut.log_str(cmd_ethtool)
    code, out, err = dut.execute(cmd_ethtool)
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

    cmd = "cat /sys/bus/pci/drivers/iavf/module/version"
    dut.log_str(cmd)
    code, out, err = dut.execute(cmd)
    if code == 0:
        iavf_driver = out[0].strip()
    config._metadata["IAVF Driver"] = iavf_driver


def pytest_html_report_title(report) -> None:
    """modifying the title  of html report"""
    report.title = "SR-IOV Test Report"


def parse_file_for_field(file_path, field) -> str:
    lines = []
    field_str = ""
    with open(file_path) as f:
        lines = f.readlines()
    for line in lines:
        field_index = line.find(field)
        if field_index != -1:
            field_str = (line[field_index + len(field):]).strip()
        if field_str:
            break
    return field_str


@pytest.fixture(autouse=True)
def _report_extras(extra, request, settings, monkeypatch) -> None:
    monkeypatch.chdir(request.fspath.dirname)

    try:
        # This is assuming the current working directory contains the test
        # specification.
        case_id = parse_file_for_field(
            request.module.__file__, settings.config["tests_id_field"]
        )
        case_name = parse_file_for_field(
            settings.config["tests_doc_file"], settings.config["tests_name_field"]
        )

        if case_name != "":
            repo = git.Repo(search_parent_directories=True)
            sha = repo.head.object.hexsha
            script_dir = os.path.dirname(os.path.realpath(__file__))
            uuid_mapping_file_path = script_dir + "/uuid_mapping.yaml"
            uuid_mapping_file = ""
            file = open(uuid_mapping_file_path, "r+")
            uuid_mapping_file = yaml.safe_load(file)
            if not uuid_mapping_file:
                uuid_mapping_file = {}
            print(uuid_mapping_file)
            if case_id not in uuid_mapping_file:
                test_dir = os.path.dirname(request.module.__file__).split(os.sep)[-1]
                link = (
                    settings.config["github_tests_path"].replace("main", sha)
                    + "/"
                    + test_dir
                    + "/"
                    + settings.config["tests_doc_file"]
                )
                try:
                    r = requests.head(link)
                except requests.ConnectionError:
                    print("Failed connection")
                if r and (r.status_code == 200 or r.status_code == 301):
                    temp_uuid_map = {case_id: link}
                    yaml.dump(temp_uuid_map, file)
                else:
                    link = None
            else:
                link = uuid_mapping_file[case_id]
            file.close()
            html_content = "<p>Local Test Case ID: " + case_id + "</p>"
            if link:
                html_content += (
                    '<p>Link to the test specification: <a href="'
                    + link
                    + '">'
                    + case_name
                    + " Documentation</a></p>"
                )
            extra.append(extras.html(html_content))
    except Exception:
        return


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--iteration",
        action="store",
        default="1",
        help="Iterations for robustness test cases",
    )
    parser.addoption(
        "--skipclean",
        action="store_true",
        default=False,
        help="Do not clean up when a test case fails",
    )


def pytest_generate_tests(metafunc) -> None:
    if "execution_number" in metafunc.fixturenames:
        if metafunc.config.getoption("iteration"):
            end = int(metafunc.config.option.iteration)
        metafunc.parametrize("execution_number", range(end))


@pytest.fixture(scope="session")
def skipclean(request):
    return request.config.option.skipclean
