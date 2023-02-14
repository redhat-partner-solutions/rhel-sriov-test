import git
import os
import pytest
from pytest_html import extras
from sriov.common.config import Config
from sriov.common.configtestdata import ConfigTestData
from sriov.common.exec import ShellHandler
from sriov.common.utils import (
    cleanup_after_ping,
    reset_mtu,
    set_pipefail,
    stop_testpmd_in_tmux,
    cleanup_after_ping_ipv6,
)


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
    dut: ShellHandler,
    trafficgen: ShellHandler,
    settings,
    testdata,
    skipclean: bool,
    request,
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
    cleanup_after_ping_ipv6(trafficgen, dut, testdata)
    assert reset_mtu(trafficgen, dut, testdata)

    # DU commands need to run after the stop_testpmd and cleanup above
    for i in range(settings.config["randomly_terminate_max_vfs"]):
        stop_testpmd_in_tmux(dut, testdata.tmux_session_name + str(i))

    reset_command(dut, testdata)


def pytest_configure(config: Config) -> None:
    ShellHandler.debug_cmd_execute = config.getoption("--debug-execute")
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
        case_name = parse_file_for_field(
            settings.config["tests_doc_file"], settings.config["tests_name_field"]
        )

        if case_name != "":
            sha = ""
            git_tag = ""
            try:
                repo = git.Repo(search_parent_directories=True)
                sha = repo.head.commit
                # This will assume that there is one tag per commit.
                for tag in repo.tags:
                    if tag.commit == sha:
                        git_tag = tag
                        break
            except Exception:
                pass

            test_dir = os.path.dirname(request.module.__file__).split(os.sep)[-1]
            if git_tag:
                link = (
                    settings.config["github_tests_path"].replace("main", str(git_tag))
                    + "/"
                    + test_dir
                    + "/"
                    + settings.config["tests_doc_file"]
                )
            elif sha:
                link = (
                    settings.config["github_tests_path"].replace("main", sha.hexsha)
                    + "/"
                    + test_dir
                    + "/"
                    + settings.config["tests_doc_file"]
                )
            else:
                case_name = "No tag or commit hash: No Link to"
                link = "#"

            extra.append(
                extras.html(
                    '<p>Link to the test specification: <a href="'
                    + link
                    + '">'
                    + case_name
                    + " Documentation</a></p>"
                )
            )
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
    parser.addoption(
        "--debug-execute",
        action="store_true",
        default=False,
        help="Debug command execute",
    )


def pytest_generate_tests(metafunc) -> None:
    if "execution_number" in metafunc.fixturenames:
        if metafunc.config.getoption("iteration"):
            end = int(metafunc.config.option.iteration)
        metafunc.parametrize("execution_number", range(end))


@pytest.fixture(scope="session")
def skipclean(request):
    return request.config.option.skipclean
