import pytest
import random
import time
from sriov.common.utils import (
    get_driver,
    start_tmux,
    stop_tmux,
    create_vfs,
    execute_and_assert,
    execute_until_timeout,
    bind_driver,
    wait_tmux_testpmd_ready,
    stop_testpmd_in_tmux,
    prepare_ping_test,
)


@pytest.mark.parametrize("options", (None, "rebind_pf", "rebind_vf"))
def test_SR_IOV_RandomlyTerminate_DPDK(dut, trafficgen, settings, testdata, options):
    """A robustness test to ensure that randomly killed and restarted testpmd containers
       recover. Permutations are necessary for random termination, random termination
       with iavf binding, and resetting the PF. Adapted from the original pkstress shell
       script written by Patrick Kutch.

    Args:
        dut:        ssh connection obj
        trafficgen: ssh connection obj
        settings:   settings obj
        testdata:   testdata obj
        options:    None, rebind_pf, or rebind_vf
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

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_ip = testdata.trafficgen_ip
    dut_ip = testdata.dut_ip
    vf0_mac = testdata.dut_mac
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    pf_pci = settings.config["dut"]["interface"]["pf1"]["pci"]

    # Bind the PF driver
    pf_driver = get_driver(dut, pf)
    assert bind_driver(dut, pf_pci, pf_driver)

    # Set hugepages (NOTE: Currently not implemented in any tests)

    # Set PF up and create VFs
    steps = ["modprobe vfio-pci", f"ip link set {pf} up"]
    execute_and_assert(dut, steps, 0, 0.1)

    assert create_vfs(dut, pf, 2)

    # Set vf0 mac
    cmd = [f"ip link set {pf} vf 0 mac {vf0_mac}"]
    execute_and_assert(dut, cmd, 0)

    # Bind VF0 to vfio-pci
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, vf_pci, "vfio-pci")

    # Start first instance of testpmd in echo mode
    dpdk_img = settings.config["dpdk_img"]
    cpus = settings.config["dut"]["pmd_cpus"]
    name = "random_terminate"
    tmux_cmd = (
        f"podman run -it --name {name} --rm --privileged "
        "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules "
        f"--cpuset-cpus {cpus} {dpdk_img} dpdk-testpmd -l {cpus} "
        f"-n 4 -a {vf_pci} "
        "-- --nb-cores=2 -i"
    )
    print(tmux_cmd)
    tmux_session = testdata.tmux_session_name
    assert start_tmux(dut, tmux_session, tmux_cmd)

    trafficgen_vlan = 0
    trafficgen_mac = None  # None means no need to set arp entry on DUT
    assert prepare_ping_test(
        trafficgen,
        trafficgen_pf,
        trafficgen_vlan,
        trafficgen_ip,
        trafficgen_mac,
        dut,
        dut_ip,
        vf0_mac,
        testdata,
    )

    ping_cmd = f"ping -W 1 -i 0.2 {dut_ip}"
    assert start_tmux(trafficgen, "ping_tmux", ping_cmd)

    end = time.time() + 60 * settings.config["randomly_terminate_test_length"]
    while end > time.time():
        assert wait_tmux_testpmd_ready(dut, tmux_session, 15)
        if "randomly_terminate_test_chance" in settings.config:
            if random.random() < settings.config["randomly_terminate_test_chance"]:
                steps = [f"podman kill {name}"]
                execute_and_assert(dut, steps, 0)

                # Ensure that the container is killed before proceeding
                steps = f"podman ps | grep {name}"
                execute_until_timeout(dut, steps, 10, 1)

                if options:
                    if options == "rebind_pf":
                        assert bind_driver(dut, pf_pci, pf_driver)
                    elif options == "rebind_vf":
                        assert bind_driver(dut, vf_pci, "vfio-pci")
                assert start_tmux(dut, tmux_session, tmux_cmd)
                assert wait_tmux_testpmd_ready(dut, tmux_session, 15)

                # Baseline stats
                stats_steps = [
                    f"tmux send-keys -t {tmux_session} 'show fwd stats all' ENTER",
                    f"tmux capture-pane -pt {tmux_session} | grep TX-packets",
                ]
                stats_outs, errs = execute_and_assert(dut, stats_steps, 0)

                steps = [
                    f"tmux send-keys -t {tmux_session} 'set fwd icmpecho' ENTER",
                    f"tmux send-keys -t {tmux_session} 'start' ENTER",
                ]
                execute_and_assert(dut, steps, 0)

                # Wait one ping before attempting to assess if testpmd if transmitting
                time.sleep(0.2)
                # Check stats after setting icmpecho and starting testpmd
                stats_outs_2, errs = execute_and_assert(dut, stats_steps, 0)

                if stats_outs[1] == stats_outs_2[1]:
                    print(stats_outs)
                    print(stats_outs_2)
                    stop_testpmd_in_tmux(dut, tmux_session)
                    assert False, "testpmd not transmitting"

        else:
            stop_testpmd_in_tmux(dut, tmux_session)
            assert False, "randomly_terminate_test_chance not set in config"

    assert stop_tmux(trafficgen, "ping_tmux")
    stop_testpmd_in_tmux(dut, tmux_session)
