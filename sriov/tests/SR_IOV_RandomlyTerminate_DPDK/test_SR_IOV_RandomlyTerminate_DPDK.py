import pytest
import random
import time
from sriov.common.utils import (
    start_tmux,
    create_vfs,
    execute_and_assert,
    execute_until_timeout,
    bind_driver,
    wait_tmux_testpmd_ready,
    get_pci_address,
    setup_hugepages,
)


def get_container_cmd(
    container_manager, container_volumes, name, cpus, dpdk_img, vf_pci
):
    tmux_cmd = (
        f"{container_manager} run -it --name {name} --rm --privileged "
        f"{container_volumes}"
        f" --cpuset-cpus {cpus} {dpdk_img} dpdk-testpmd -l {cpus} "
        f"-n 4 -a {vf_pci} "
        "-- --nb-cores=1 --forward=txonly -i"
    )
    return tmux_cmd


def get_testpmd_cpus(control_core, i):
    cpus = str(control_core) + "," + str(control_core + i + 1)
    return cpus


@pytest.mark.parametrize("options", (None, "rebind_vf"))
def test_SR_IOV_RandomlyTerminate_DPDK(dut, settings, testdata, options):
    """A robustness test to ensure that randomly killed and restarted testpmd containers
       recover. Permutations are necessary for random termination and random termination
       with iavf binding. Adapted from the original pkstress shell
       script written by Patrick Kutch.

    Args:
        dut:        ssh connection obj
        settings:   settings obj
        testdata:   testdata obj
        options:    None, or rebind_vf
    """
    print(
        "Test length: "
        + str(settings.config["randomly_terminate_test_length"])
        + " minutes"
    )
    print(
        "Chance of killing testpmd: "
        + str(settings.config["randomly_terminate_test_chance"])
    )

    if "randomly_terminate_test_chance" not in settings.config:
        assert False, "randomly_terminate_test_chance not set in config"
    elif "randomly_terminate_max_vfs" not in settings.config:
        assert False, "randomly_terminate_max_vfs not set in config"
    elif "randomly_terminate_control_core" not in settings.config:
        assert False, "randomly_terminate_control_core not set in config"
    elif "randomly_terminate_test_length" not in settings.config:
        assert False, "randomly_terminate_test_length not set in config"

    pf = settings.config["dut"]["interface"]["pf1"]["name"]

    # Get maximum amount of VFs
    max_vfs_cmd = ["cat /sys/class/net/" + pf + "/device/sriov_totalvfs"]
    outs, errs = execute_and_assert(dut, max_vfs_cmd, 0)
    max_vfs = int(outs[0][0].strip())

    # Get maximum amount of CPUs
    max_cpus_cmd = ["grep -c processor /proc/cpuinfo"]
    outs, errs = execute_and_assert(dut, max_cpus_cmd, 0)
    max_cpus = int(
        int(outs[0][0].strip()) - 3  # 2 cores for housekeeping, 1 control core
    )

    # Create the minimum acceptable number of VFs
    num_vfs = min(max_vfs, max_cpus, settings.config["randomly_terminate_max_vfs"])
    assert create_vfs(dut, pf, num_vfs)
    setup_hugepages(dut, num_vfs)

    base_name = "random_terminate"
    dpdk_img = settings.config["dpdk_img"]
    tmux_list = []
    for i in range(num_vfs):
        # Bind VF0 to vfio-pci
        vf_pci = get_pci_address(dut, pf + "v" + str(i))
        assert bind_driver(dut, vf_pci, "vfio-pci")

        cpus = get_testpmd_cpus(settings.config["randomly_terminate_control_core"], i)
        name = base_name + str(i)
        tmux_cmd = get_container_cmd(
            settings.config["container_manager"],
            settings.config["container_volumes"],
            name,
            cpus,
            dpdk_img,
            vf_pci,
        )

        # Start instance of testpmd
        tmux_session = testdata.tmux_session_name + str(i)
        assert start_tmux(dut, tmux_session, tmux_cmd)
        assert wait_tmux_testpmd_ready(dut, tmux_session, 15)
        tmux_list.append([tmux_session, vf_pci])

    end = time.time() + 60 * settings.config["randomly_terminate_test_length"]
    while end > time.time():
        for i in range(num_vfs):
            if random.random() < settings.config["randomly_terminate_test_chance"]:
                cpus = get_testpmd_cpus(
                    settings.config["randomly_terminate_control_core"], i
                )
                name = base_name + str(i)
                tmux_session = tmux_list[i][0]
                vf_pci = tmux_list[i][1]
                tmux_cmd = get_container_cmd(
                    settings.config["container_manager"],
                    settings.config["container_volumes"],
                    name,
                    cpus,
                    dpdk_img,
                    vf_pci,
                )

                # Kill the container
                steps = [f"{settings.config['container_manager']} kill {name}"]
                execute_and_assert(dut, steps, 0)

                # Ensure that the container is killed before proceeding
                steps = (
                    f"{settings.config['container_manager']} ps -f name={name}$ | "
                    f"grep {name}"
                )
                assert execute_until_timeout(dut, steps, 10, 1)

                # Restart the container, as well as rebind drivers if required
                if options:
                    if options == "rebind_vf":
                        assert bind_driver(dut, vf_pci, "vfio-pci")

                # Ensure that the tmux session has ended before proceeding
                steps = f"tmux has-session -t {tmux_session}"
                assert execute_until_timeout(dut, steps, 10, 1)

                assert start_tmux(dut, tmux_session, tmux_cmd)
                assert wait_tmux_testpmd_ready(dut, tmux_session, 15)

                # Start testpmd
                steps = [
                    f"tmux send-keys -t {tmux_session} 'start' ENTER",
                ]
                execute_and_assert(dut, steps, 0)

                # Baseline stats
                stats_steps = [
                    f"tmux send-keys -t {tmux_session} 'show fwd stats all' ENTER",
                    f"tmux capture-pane -pt {tmux_session} | tail -4 | grep TX-packets",
                ]
                stats_outs, errs = execute_and_assert(dut, stats_steps, 0, 0.1)
                stats_outs_2, errs = execute_and_assert(dut, stats_steps, 0, 0.1)

                # Ensure testpmd is transmitting
                if stats_outs[1] == stats_outs_2[1]:
                    print(stats_outs)
                    print(stats_outs_2)
                    assert False, "testpmd not transmitting"
