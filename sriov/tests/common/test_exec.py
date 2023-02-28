import logging
import time


LOGGER = logging.getLogger(__name__)


def test_timeout_handler(dut):
    try:
        dut.timeout_handler(0, 0)
        assert False  # This should always be short circuited
    except Exception as e:
        assert True
        assert "timeout" in str(e)


def test_execute_cmd_success(dut):
    cmd = "cat /proc/1/status"
    dut.log_str(cmd)
    code, out, err = dut.execute(cmd)
    assert code == 0
    assert "systemd" in out[0]


def test_execute_cmd_fail(dut):
    cmd = "cat /proc/-1/status"
    dut.log_str(cmd)
    code, out, err = dut.execute(cmd)
    assert code != 0
    assert "No such file or directory" in err[0]


def test_execute_cmd_timeout(dut):
    cmd = "sleep 6s"
    dut.log_str(cmd)
    code, out, err = dut.execute(cmd)
    # Allow for original sleep to end (5 second timeout + 1 second) before cleanup
    time.sleep(1)
    assert code != 0 and "timeout" in err[0]


def test_execute_cmd_with_delay(dut):
    cmd = "sleep 1s"
    dut.log_str(cmd)
    code, out, err = dut.execute(cmd)
    assert code == 0


def test_start_and_stop_testpmd(dut, settings):
    pf_pci = settings.config["dut"]["interface"]["pf1"]["pci"]
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]

    pf_device_path = "/sys/bus/pci/devices/" + pf_pci
    vf_device_path = "/sys/bus/pci/devices/" + vf_pci
    steps = [
        "modprobe vfio-pci",
        "echo 0 > " + pf_device_path + "/sriov_numvfs",
        "echo 1 > " + pf_device_path + "/sriov_numvfs",
        "echo " + vf_pci + " > " + vf_device_path + "/driver/unbind",
        "echo vfio-pci > " + vf_device_path + "/driver_override",
        "echo " + vf_pci + " > " + "/sys/bus/pci/drivers/vfio-pci/bind",
    ]
    for step in steps:
        dut.log_str(step)
        code, out, err = dut.execute(step)
        assert code == 0, step
    testpmd_container_cmd = (
        f"{settings.config['container_manager']} run -it --rm --privileged "
        "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules "
        "--cpuset-cpus 30,32,34 docker.io/patrickkutch/dpdk:v21.11 "
        "dpdk-testpmd -l 30,32,34 -n 4 -a " + vf_pci + " -- --nb-cores=2 -i"
    )
    code, out, err = dut.start_testpmd(testpmd_container_cmd)
    assert code == 0
    assert dut.testpmd_active()
    assert dut.stop_testpmd() == 0
    # test after quit from testpmd session, ssh session is ready for shell cmd
    time.sleep(1)
    cmd = "echo ALIVE"
    dut.log_str(cmd)
    code, out, err = dut.execute(cmd)
    assert code == 0, err
    print(out)
    assert out[0].strip("\n") == "ALIVE", out
