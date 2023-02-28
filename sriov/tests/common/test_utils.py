from sriov.common.utils import (
    get_driver,
    bind_driver,
    start_tmux,
    stop_tmux,
    execute_and_assert,
    get_intf_mac,
    get_pci_address,
    config_interface,
    clear_interface,
    set_pipefail,
    create_vfs,
    execute_until_timeout,
    get_vf_mac,
    add_arp_entry,
    rm_arp_entry,
    prepare_ping_test,
    cleanup_after_ping,
    set_mtu,
    reset_mtu,
    no_zero_macs_vf,
    set_vf_mac,
    verify_vf_address,
    vfs_created,
    no_zero_macs_pf,
)


def test_get_pci_address(dut, settings):
    pf_pci = settings.config["dut"]["interface"]["pf1"]["pci"]
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    assert pf_pci == get_pci_address(dut, pf_name)

    assert create_vfs(dut, pf_name, 1)
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    vf_name = settings.config["dut"]["interface"]["vf1"]["name"]
    assert vf_pci == get_pci_address(dut, vf_name)


def test_get_driver(dut, settings):
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    assert get_driver(dut, pf_name) == "ice"


def test_bind_driver(dut, settings):
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    assert create_vfs(dut, pf_name, 1)
    vf_pci = settings.config["dut"]["interface"]["vf1"]["pci"]
    assert bind_driver(dut, vf_pci, "vfio-pci")


def test_config_and_clear_interface(dut, trafficgen, settings, testdata):
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_vlan = 0
    trafficgen_ip = "1.2.3.4"
    assert clear_interface(trafficgen, trafficgen_pf, trafficgen_ip, trafficgen_vlan)
    assert config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, trafficgen_ip)

    step = [f"ip addr show {trafficgen_pf}"]
    outs, errs = execute_and_assert(trafficgen, step, 0)

    ip_addr_found = False
    for out in outs[0]:
        if trafficgen_ip in out:
            ip_addr_found = True
            break

    assert ip_addr_found is True

    assert clear_interface(trafficgen, trafficgen_pf, trafficgen_ip, trafficgen_vlan)

    outs, errs = execute_and_assert(trafficgen, step, 0)

    ip_addr_found = False
    for out in outs[0]:
        if trafficgen_ip in out:
            ip_addr_found = True
            break

    assert ip_addr_found is False


def test_config_and_clear_interface_fail(dut, trafficgen, settings, testdata):
    trafficgen_pf = "test"
    trafficgen_vlan = 0
    trafficgen_ip = testdata.trafficgen_ip
    try:
        config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, trafficgen_ip)
        assert False  # Should always short circuit this
    except Exception:
        assert True

    try:
        assert clear_interface(
            trafficgen, trafficgen_pf, trafficgen_ip, trafficgen_vlan
        )
        assert False  # Should always short circuit this
    except Exception:
        assert True


def test_add_and_rm_arp_entry(dut, trafficgen, settings, testdata):
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_vlan = 0
    trafficgen_ip = testdata.trafficgen_ip
    assert clear_interface(trafficgen, trafficgen_pf, trafficgen_vlan)
    assert config_interface(trafficgen, trafficgen_pf, trafficgen_vlan, trafficgen_ip)

    dut_ip = testdata.dut_ip
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    create_vfs(dut, pf, 1)
    vf0_mac = get_vf_mac(dut, pf, 0)
    assert add_arp_entry(trafficgen, dut_ip, vf0_mac)

    step = ["arp -a"]
    outs, errs = execute_and_assert(trafficgen, step, 0)

    ip_arp_found = False
    mac_arp_found = False
    for out in outs[0]:
        if dut_ip in out:
            ip_arp_found = True
        if vf0_mac in out:
            mac_arp_found = True

    assert (ip_arp_found is True) and (mac_arp_found is True)

    assert rm_arp_entry(trafficgen, dut_ip)

    outs, errs = execute_and_assert(trafficgen, step, 0)

    ip_arp_found = False
    mac_arp_found = False
    for out in outs[0]:
        if dut_ip in out:
            ip_arp_found = True
        if vf0_mac in out:
            mac_arp_found = True

    assert (ip_arp_found is False) and (mac_arp_found is False)


def test_add_and_rm_arp_entry_fail(dut, trafficgen):
    try:
        add_arp_entry(trafficgen, "1.2.3.4", "test")
        assert False  # Should always short circuit this
    except Exception:
        assert True

    try:
        rm_arp_entry(trafficgen, "1.2.3.4")
        assert False  # Should always short circuit this
    except Exception:
        assert True


def test_tmux(dut, testdata):
    name = testdata.tmux_session_name
    assert start_tmux(dut, name, "sleep 8")
    assert stop_tmux(dut, name)


def test_prepare_and_cleanup_ping_test(dut, trafficgen, testdata, settings):
    ping_cmd = "ping -W 1 -c 1 {}".format(testdata.dut_ip)
    assert execute_until_timeout(dut, ping_cmd) is False

    trafficgen_ip = testdata.trafficgen_ip
    dut_ip = testdata.dut_ip
    vf0_mac = testdata.dut_mac
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        "ip link set {}v0 down".format(pf),
        "ip link set {} vf 0 mac {}".format(pf, vf0_mac),
        "ip link set {}v0 up".format(pf),
        "ip add add {}/24 dev {}v0".format(dut_ip, pf),
    ]

    create_vfs(dut, pf, 1)

    execute_and_assert(dut, steps, 0, 0.1)

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    trafficgen_vlan = 0

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

    assert execute_until_timeout(dut, ping_cmd) is True

    assert cleanup_after_ping(trafficgen, dut, testdata)


def test_set_and_reset_mtu(dut, trafficgen, testdata, settings):
    assert set_pipefail(dut)
    default_mtu = 1500
    pf_name = settings.config["dut"]["interface"]["pf1"]["name"]
    default_cmd = [f'ip link show {pf_name} | grep "mtu {default_mtu}"']
    execute_and_assert(dut, default_cmd, 0)

    assert create_vfs(dut, pf_name, 1)
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    mtu = 1501
    assert set_mtu(trafficgen, trafficgen_pf, dut, pf_name, 0, mtu, testdata)
    cmd = [f'ip link show {pf_name} | grep "mtu {mtu}"']
    execute_and_assert(dut, cmd, 0)

    assert reset_mtu(trafficgen, dut, testdata)
    execute_and_assert(dut, default_cmd, 0)


def test_get_intf_mac(trafficgen, settings):
    mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    pf_name = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    assert mac == get_intf_mac(trafficgen, pf_name)


def test_vf_functions(dut, settings, testdata):
    """A combined test which tests create_vfs, get_vf_mac, set_vf_mac,
    verify_vf_address, vfs_created, no_zero_macs_vf, and no_zero_macs_vf.
    """
    custom_mac = "00:00:00:00:00:01"

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    assert create_vfs(dut, pf, 1) is True
    vf_1_mac = get_vf_mac(dut, pf, 0)

    assert no_zero_macs_vf(dut, pf, 1) is True
    assert set_vf_mac(dut, pf, 0, custom_mac) is True
    vf_zeros_mac = get_vf_mac(dut, pf, 0)
    assert vf_1_mac != vf_zeros_mac
    assert vf_zeros_mac == custom_mac

    assert verify_vf_address(dut, pf, 0, custom_mac) is True

    assert vfs_created(dut, pf, 1) is True
    assert vfs_created(dut, pf, 0) is False

    assert no_zero_macs_pf(dut, pf) is True
    assert no_zero_macs_vf(dut, pf, 1) is True


def test_set_pipefail(dut):
    test_cmd = "false | echo test"
    dut.log_str(test_cmd)
    code, _, err = dut.execute(test_cmd)
    assert code != 0


def test_execute_and_assert(dut):
    invalid_cmds = ["invalid_command", "also_invalid"]
    out, err = execute_and_assert(dut, invalid_cmds, 127)

    valid_cmds = ["echo Hello", "ls"]
    out, err = execute_and_assert(dut, valid_cmds, 0)
    assert "Hello" in out[0][0]
