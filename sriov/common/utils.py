import re
from sriov.common.configtestdata import ConfigTestData
from sriov.common.exec import ShellHandler
import time
from typing import Tuple


def get_pci_address(ssh_obj: ShellHandler, iface: str) -> str:
    """Get the PCI address of an interface

    Args:
        ssh_obj:     ssh_obj to the remote host
        iface (str): interface name, example: "ens2f0"

    Returns:
        PCI address (str), example "0000:17:00.0"

    Raises:
        Exception: command failure
    """
    cmd = "ethtool -i {}".format(iface) + " | awk '/bus-info:/{print $2;}'"
    ssh_obj.log_str(cmd)
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    return out[0].strip("\n")


def bind_driver(ssh_obj: ShellHandler, pci: str, driver: str, timeout: int = 5) -> bool:
    """Bind the PCI address to the driver

    Args:
        ssh_obj:       ssh_obj to the remote host
        pci (str):     PCI address, example "0000:17:00.0"
        driver (str):  driver name, example "vfio-pci"
        timeout (int): seconds of timeout for execute, default of 5

    Returns:
        True: on success of binding

    Raises:
        Exception: command failure
    """
    device_path = "/sys/bus/pci/devices/" + pci
    steps = [
        "modprobe {}".format(driver),
        "echo {} > {}/driver/unbind".format(pci, device_path),
        "echo {} > {}/driver_override".format(driver, device_path),
        "echo {} > /sys/bus/pci/drivers/{}/bind".format(pci, driver),
    ]
    for step in steps:
        ssh_obj.log_str(step)
        code, out, err = ssh_obj.execute(step, timeout)
        if code != 0:
            raise Exception(err)
    return True


def bind_driver_with_dpdk(settings: object, ssh_obj: ShellHandler, pci: str, driver: str, timeout: int = 5) -> bool:
    """ Bind the PCI address to the driver using dpdk-devbind.py in the dpdk container

    Args:
        ssh_obj:       ssh_obj to the remote host
        pci (str):     PCI address, example "0000:17:00.0"
        driver (str):  driver name, example "vfio-pci"
        timeout (int): seconds of timeout for execute, default of 5

    Returns:
        True: on success of binding

    Raises:
        Exception: command failure
    """

    # use dpdk-devbind.py within the dpdk container to do the binding
    dpdk_devbind_cmd = (
            f"{settings.config['container_manager']} run -it --rm --privileged "
            f"{settings.config['container_volumes']} "
            f"{settings.config['dpdk_img']} dpdk-devbind.py -b {driver} {pci}\n")

    steps = [
        ("modprobe {}".format(driver), None),
        (dpdk_devbind_cmd, "Error")
    ]

    for step, errorOnStr in steps:
        ssh_obj.log_str(step)
        # use executeWithSearch because you cannot get the errorcode
        # from the container, so we search stdout for a desired error string
        code, out, err = ssh_obj.executeWithSearch(step, errorOnStr, timeout)
        if code != 0:
            raise Exception(err)
    return True


def get_driver(ssh_obj: ShellHandler, intf: str, timeout: int = 5) -> str:
    """Get the interface driver

    Args:
        ssh_obj:       ssh_obj to the remote host
        intf (str):    interface name
        timeout (int): seconds of timeout for execute, default of 5

    Returns:
        (str) driver: on success

    Raises:
        Exception: command failure
    """
    step = f"ethtool -i {intf} | grep driver | cut -c9-"
    ssh_obj.log_str(step)
    code, out, err = ssh_obj.execute(step, timeout)
    if code != 0:
        raise Exception(err)

    return out[0].strip("\n")


def config_interface(ssh_obj: ShellHandler, intf: str, vlan: int, ip: str) -> bool:
    """Config an IP address on VLAN interface; if VLAN is 0, config IP on
        main interface

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name
        vlan (int): VLAN ID
        ip (str):   IP address

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    if vlan != 0:
        steps = [
            f"ip link del {intf}.{vlan} 2>/dev/null || true",
            f"ip link add link {intf} name {intf}.{vlan} type vlan id {vlan}",
            f"ip add add {ip}/24 dev {intf}.{vlan}",
            f"ip link set {intf}.{vlan} up",
        ]
    else:
        steps = [
            f"ip add del {ip}/24 dev {intf} 2>/dev/null || true",
            f"ip add add {ip}/24 dev {intf}",
        ]
    for step in steps:
        ssh_obj.log_str(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
    return True


def config_interface_ipv6(
    ssh_obj: ShellHandler, intf: str, vlan: int, ipv6: str
) -> bool:
    """Config an IPv6 address on VLAN interface; if VLAN is 0, config IPv6 on
        main interface

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name
        vlan (int): VLAN ID
        ipv6 (str): IPv6 address

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    if vlan != 0:
        steps = [
            f"ip -6 add del {ipv6}/64 dev {intf} 2>/dev/null || true",
            f"ip link add link {intf} name {intf}.{vlan} type vlan id {vlan}",
            f"ip -6 add add {ipv6}/64 dev {intf}.{vlan}",
            f"ip link set {intf}.{vlan} up",
        ]
    else:
        steps = [
            f"ip -6 add del {ipv6}/64 dev {intf} 2>/dev/null || true",
            f"ip -6 add add {ipv6}/64 dev {intf}",
        ]
    for step in steps:
        ssh_obj.log_str(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
    return True


def clear_interface(ssh_obj: ShellHandler, intf: str, ip: str, vlan: int = 0) -> bool:
    """Clear the IP address from the VLAN interface and the main interface

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name
        ip (str): IP address
        vlan (int): VLAN ID

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    steps = [f"ip address del {ip}/24 dev {intf} 2> /dev/null || true"]
    if vlan != 0:
        steps.append(f"ip link del {intf}.{vlan} || true")

    for step in steps:
        ssh_obj.log_str(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
    return True


def clear_interface_ipv6(
    ssh_obj: ShellHandler, intf: str, ipv6: str, vlan: int = 0
) -> bool:
    """Clear the IPv6 address from the VLAN interface and the main interface

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name
        ipv6 (str): ipv6 address
        vlan (int): VLAN ID

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    steps = [f"ip -6 addr del {ipv6}/64 dev {intf} 2> /dev/null || true"]
    if vlan != 0:
        steps.append(f"ip link del {intf}.{vlan} || true")

    for step in steps:
        ssh_obj.log_str(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
    return True


def add_arp_entry(ssh_obj: ShellHandler, ip: str, mac: str) -> bool:
    """Add a static ARP entry

    Args:
        ssh_obj:   SSH connection obj
        ip (str):  IP address
        mac (str): MAC address

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    cmd = f"arp -s {ip} {mac}"
    ssh_obj.log_str(cmd)
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    return True


def rm_arp_entry(ssh_obj: ShellHandler, ip: str) -> bool:
    """Remove a static ARP entry

    Args:
        ssh_obj:  SSH connection obj
        ip (str): IP address

    Raises:
        Exception: command failure
    """
    cmd = f"arp -d {ip} || true"  # not a failure if the ip entry not exist
    ssh_obj.log_str(cmd)
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    return True


def prepare_ping_test(
    tgen: ShellHandler,
    tgen_intf: str,
    tgen_vlan: int,
    tgen_ip: str,
    tgen_mac: str,
    dut: ShellHandler,
    dut_ip: str,
    dut_mac: str,
    testdata: ConfigTestData,
) -> bool:
    """Collection of steps to prepare for ping test

    Args:
        tgen (object): trafficgen ssh handler
        tgen_intf (str): trafficgen physical interface name
        tgen_vlan (int): vlan ID on the trafficgen physical interface
        tgen_ip (str): trafficgen ip address
        tgen_mac (str): trafficgen mac address;
                        set to None will not add arp entry on DUT
        dut (object): DUT ssh handler
        dut_ip (str): DUT ip address
        dut_mac (str): DUT mac address
        testdata (object): testdata object

    Returns:
        True: on success
    """
    assert clear_interface(tgen, tgen_intf, tgen_vlan)

    # Track if ping is executed when cleanup_after_ping is called for cleanup
    testdata.ping["run"] = True
    testdata.ping["tgen_intf"] = tgen_intf
    testdata.ping["tgen_vlan"] = tgen_vlan
    testdata.ping["tgen_ip"] = tgen_ip
    testdata.ping["tgen_mac"] = tgen_mac
    testdata.ping["dut_ip"] = dut_ip
    testdata.ping["dut_mac"] = dut_mac

    assert config_interface(tgen, tgen_intf, tgen_vlan, tgen_ip)
    assert add_arp_entry(tgen, dut_ip, dut_mac)
    if tgen_mac is not None:
        assert add_arp_entry(dut, tgen_ip, tgen_mac)
    return True


def prepare_ping_ipv6_test(
    tgen: ShellHandler,
    tgen_intf: str,
    tgen_vlan: int,
    tgen_ip_v6: str,
    dut_ip_v6: str,
    testdata: ConfigTestData,
) -> bool:
    """Collection of steps to prepare for ping test

    Args:
        tgen (object): trafficgen ssh handler
        tgen_intf (str): trafficgen physical interface name
        tgen_vlan (int): vlan ID on the trafficgen physical interface
        tgen_ip_v6 (str): trafficgen ipv6 address
        dut_ip_v6 (str): DUT ipv6 address
        testdata (object): testdata object

    Returns:
        True: on success
    """
    # Track if ping is executed when cleanup_after_ping is called for cleanup
    testdata.ping["run_ipv6"] = True
    testdata.ping["tgen_intf"] = tgen_intf
    testdata.ping["tgen_vlan"] = tgen_vlan
    testdata.ping["tgen_ip_v6"] = tgen_ip_v6
    testdata.ping["dut_ip_v6"] = dut_ip_v6

    clear_interface_ipv6(tgen, tgen_intf, tgen_ip_v6, tgen_vlan)
    assert config_interface_ipv6(tgen, tgen_intf, tgen_vlan, tgen_ip_v6)
    return True


def cleanup_after_ping(
    tgen: ShellHandler, dut: ShellHandler, testdata: ConfigTestData
) -> bool:
    """Collection of steps to cleanup after ping test

    Args:
        tgen (object): trafficgen ssh handler
        dut (object): DUT ssh handler
        testdata (object): testdata object

    Returns:
        True: on success
    """
    run = testdata.ping.get("run", False)
    if run:
        testdata.ping["run"] = False
        tgen_intf = testdata.ping.get("tgen_intf")
        tgen_vlan = testdata.ping.get("tgen_vlan")
        tgen_ip = testdata.ping.get("tgen_ip")
        dut_ip = testdata.ping.get("dut_ip")
        tgen_mac = testdata.ping["tgen_mac"]
        assert rm_arp_entry(tgen, dut_ip)
        assert clear_interface(tgen, tgen_intf, tgen_ip, tgen_vlan)
        if tgen_mac is not None:
            assert rm_arp_entry(dut, tgen_ip)
    return True


def cleanup_after_ping_ipv6(
    tgen: ShellHandler, dut: ShellHandler, testdata: ConfigTestData
):
    """Collection of steps to cleanup after ipv6 ping test

    Args:
        tgen (object): trafficgen ssh handler
        dut (object): DUT ssh handler
        testdata (object): testdata object
    """
    run = testdata.ping.get("run_ipv6", False)
    if run:
        testdata.ping["run_ipv6"] = False
        tgen_intf = testdata.ping.get("tgen_intf")
        tgen_vlan = testdata.ping.get("tgen_vlan")
        tgen_ip_v6 = testdata.ping.get("tgen_ip_v6")
        dut_ip_v6 = testdata.ping.get("dut_ip_v6")
        delete_ipv6_neighbor(tgen, dut_ip_v6)
        clear_interface_ipv6(tgen, tgen_intf, tgen_ip_v6, tgen_vlan)
        delete_ipv6_neighbor(dut, tgen_ip_v6)


def set_mtu(
    tgen: ShellHandler,
    tgen_pf: str,
    dut: ShellHandler,
    dut_pf: str,
    dut_vf: int,
    mtu: int,
    testdata: ConfigTestData,
) -> bool:
    """Set MTU on trafficgen and DUT

    Args:
        tgen (object): trafficgen ssh connection
        tgen_pf (str): trafficgen PF
        dut (object): DUT ssh connection
        dut_pf (str): DUT PF
        dut_vf (int): DUT VF id
        mtu (int): MTU size in bytes
        testdata (object): testdata object

    Returns:
        True: on success
    """
    testdata.mtu["changed"] = True
    testdata.mtu["tgen_intf"] = tgen_pf
    testdata.mtu["du_intf"] = dut_pf
    testdata.mtu["dut_vf"] = dut_vf

    steps = [f"ip link set {tgen_pf} mtu {mtu}"]
    execute_and_assert(tgen, steps, 0)

    steps = [
        f"ip link set {dut_pf} mtu {mtu}",
        f"ip link set {dut_pf}v{dut_vf} mtu {mtu}",
    ]
    execute_and_assert(dut, steps, 0, timeout=0.1)
    return True


def reset_mtu(tgen: ShellHandler, dut: ShellHandler, testdata: ConfigTestData) -> bool:
    """Reset MTU on trafficgen and DUT

    Args:
        tgen (object): trafficgen ssh connection
        dut (object): DUT ssh connection
        testdata (object): testdata object

    Returns:
        True: on success
    """
    changed = testdata.mtu.get("changed", False)
    if changed:
        tgen_intf = testdata.mtu.get("tgen_intf")
        du_intf = testdata.mtu.get("du_intf")
        tgen_cmd = f"ip link set {tgen_intf} mtu 1500"
        tgen.log_str(tgen_cmd)
        tgen.execute(tgen_cmd)
        dut_cmd = f"ip link set {du_intf} mtu 1500"
        dut.log_str(dut_cmd)
        dut.execute(dut_cmd)
    return True


def start_tmux(ssh_obj: ShellHandler, name: str, cmd: str) -> bool:
    """Run cmd in a tmux session

    Args:
        ssh_obj:    SSH connection obj
        name (str): tmux session name
        cmd (str):  a single command to run

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """

    steps = [
        f"tmux kill-session -t {name} || true",
        f"tmux new-session -s {name} -d {cmd}",
    ]

    for step in steps:
        ssh_obj.log_str(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
    return True


def stop_tmux(ssh_obj: ShellHandler, name: str) -> bool:
    """Stop tmux session

    Args:
        ssh_obj:    SSH connection obj
        name (str): tmux session name

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    cmd = f"tmux kill-session -t {name} || true"
    ssh_obj.log_str(cmd)
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    return True


def get_intf_mac(ssh_obj: ShellHandler, intf: str) -> str:
    """Get the MAC address from the interface name

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name

    Returns:
        str: Interface MAC address

    Raises:
        Exception:  command failure
        ValueError: failure in parsing
    """
    cmd = f"cat /sys/class/net/{intf}/address"
    ssh_obj.log_str(cmd)
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    for line in out:
        if len(line.split(":")) == 6:
            return line.strip("\n")
    raise ValueError("can't parse mac address")


def get_vf_mac(ssh_obj: ShellHandler, intf: str, vf_id: int) -> str:
    """Get the MAC address from the interface's VF ID

    Args:
        ssh_obj (_type_): SSH connection obj
        intf (str):       interface name
        vf_id (int):      virtual function ID

    Returns:
        str: VF MAC address

    Raises:
        Exception:  command failure
        ValueError: failure in parsing
    """
    cmd = f"ip link show {intf} | awk '/vf {vf_id}/" + "{print $4;}'"
    ssh_obj.log_str(cmd)
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    for line in out:
        if len(line.split(":")) == 6:
            return line.strip("\n")
    raise ValueError("can't parse mac address")


def set_vf_mac(
    ssh_obj: ShellHandler,
    intf: str,
    vf_id: int,
    address: str,
    timeout: int = 10,
    interval: int = 0.1,
) -> bool:
    """Set the VF mac address

    Args:
        ssh_obj (_type_): SSH connection obj
        intf (str):       interface name
        vf_id (int):      virtual function ID
        address(str):     mac address
        timeout(int):     number of seconds to timeout
        interval(float):  polling interval in seconds

    Returns:
        True: mac address is set with success
        False: mac address can't be set before timeout
    """
    set_mac_cmd = f"ip link set {intf} vf {vf_id} mac {address}"
    ssh_obj.log_str(set_mac_cmd)
    code, out, err = ssh_obj.execute(set_mac_cmd)
    if code != 0:
        return False

    count = int(timeout / interval) + 1
    while count > 0:
        vf_mac = get_intf_mac(ssh_obj, f"{intf}v{vf_id}")
        if vf_mac == address:
            return True
        count -= 1
        time.sleep(interval)
    return False


def verify_vf_address(
    ssh_obj: ShellHandler,
    intf: str,
    vf_id: int,
    address: str,
    timeout: int = 10,
    interval: int = 0.1,
) -> bool:
    """Verify that the VF has the specified address

    Args:
        ssh_obj (_type_): SSH connection obj
        intf (str):       interface name
        vf_id (int):      virtual function ID
        address(str):     mac address
        timeout(int):     number of seconds to timeout
        interval(float):  polling interval in seconds

    Returns:
        True: The VF has the specified address
        False: The VF doesn't have the specified address before timeout
    """
    count = int(timeout / interval) + 1
    while count > 0:
        vf_mac = get_vf_mac(ssh_obj, intf, vf_id)
        print(vf_mac)
        if vf_mac == address:
            return True
        count -= 1
        time.sleep(interval)
    return False


def vfs_created(
    ssh_obj: ShellHandler, pf_interface: str, num_vfs: int, timeout: int = 10
) -> bool:
    """Check that the num_vfs of pf_interface are created before timeout

    Args:
        ssh_obj:            ssh connection obj
        pf_interface (str): name of the PF
        num_vfs (int):      number of VFs to check under PF
        timout (int):       times to check for VFs (default 10)

    Returns:
        True: all VFs are created
        False: not all VFs are created before timeout exceeded
    """
    cmd = "ls -d /sys/class/net/" + pf_interface + "v* | wc -w"
    ssh_obj.log_str(cmd)
    for i in range(timeout):
        time.sleep(1)
        code, out, err = ssh_obj.execute(cmd)
        if code != 0:
            continue
        if int(out[0].strip()) == num_vfs:
            return True
    return False


def destroy_vfs(ssh_obj: ShellHandler, pf_interface: str) -> None:
    """Destroy the VFs on pf_interface

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        pf_interface (str): name of the PF
    """
    clear_vfs = f"echo 0 > /sys/class/net/{pf_interface}/device/sriov_numvfs"
    ssh_obj.log_str(clear_vfs)
    ssh_obj.execute(clear_vfs, 60)


def create_vfs(
    ssh_obj: ShellHandler, pf_interface: str, num_vfs: int, timeout: int = 10
) -> bool:
    """Create the num_vfs of pf_interface

    Args:
        ssh_obj:            ssh connection obj
        pf_interface (str): name of the PF
        num_vfs (int):      number of VFs to create under PF
        timout (int):       times to check for VFs (default 10)

    Returns:
        True: all VFs are created
        False: not all VFs are created before timeout exceeded

    Raises:
        Exception:  failed to create VFs before timeout exceeded
    """
    destroy_vfs(ssh_obj, pf_interface)
    create_vfs = f"echo {num_vfs} > /sys/class/net/{pf_interface}/device/sriov_numvfs"
    ssh_obj.log_str(create_vfs)
    ssh_obj.execute(create_vfs, 60)
    return vfs_created(ssh_obj, pf_interface, num_vfs, timeout)


def no_zero_macs_pf(
    ssh_obj: ShellHandler, pf_interface: str, timeout: int = 10
) -> bool:
    """Check that none of the pf_interface VFs have all zero MAC addresses (from
       the pf report)

    Args:
        ssh_obj:            ssh connection obj
        pf_interface (str): name of the PF
        timout (int):       times to check for VFs (default 10)

    Returns:
        True: no interfaces have all zero MAC addresses
        False: an interface with zero MAC address was found or timeout exceeded
    """
    check_vfs = "ip -d link show " + pf_interface
    ssh_obj.log_str(check_vfs)
    for i in range(timeout):
        time.sleep(1)
        code, out, err = ssh_obj.execute(check_vfs)
        if code != 0:
            continue
        no_zeros = True
        for out_slice in out:
            if "00:00:00:00:00:00" in out_slice:
                no_zeros = False
                break
        if no_zeros:
            return True
    return False


def no_zero_macs_vf(
    ssh_obj: ShellHandler, pf_interface: str, num_vfs: int, timeout: int = 10
) -> bool:
    """Check that none of the interfaces's VFs have zero MAC addresses (from
       the vf reports)

    Args:
        ssh_obj:            ssh connection obj
        pf_interface (str): name of the PF
        num_vfs (int):      number of VFs to check under PF
        timout (int):       time to check for VFs (default 10)

    Returns:
        True: no VFs of interface have all zero MAC addresses
        False: a VF with zero MAC address was found or timeout exceeded
    """
    check_vfs = "ip -d link show " + pf_interface
    ssh_obj.log_str(check_vfs)
    for i in range(timeout):
        time.sleep(1)
        no_zeros = True
        for i in range(num_vfs):
            code, out, err = ssh_obj.execute(check_vfs + "v" + str(i))
            if code != 0:
                break
            for out_slice in out:
                if "00:00:00:00:00:00" in out_slice:
                    no_zeros = False
                    break
        if no_zeros:
            return True
    return False


def set_pipefail(ssh_obj: ShellHandler) -> bool:
    """Set the pipefail to persist errors

    Args:
        ssh_obj: ssh connection obj

    Returns:
        True: on success

    Raises:
        Exception: command failure
    """
    set_command = "set -o pipefail"
    ssh_obj.log_str(set_command)
    code, out, err = ssh_obj.execute(set_command)
    if code != 0:
        raise Exception(err)
    return True


def execute_and_assert(
    ssh_obj: ShellHandler, cmds: list, exit_code: int, timeout: int = 0
) -> Tuple[list, list]:
    """Execute the list of commands, assert exit code, and return stdouts and stderrs

    Args:
        ssh_obj:         ssh connection obj
        cmds (list):     list of str commands to run
        exit_code (int): the code to assert
        timeout (int):   optional timeout between cmds (default 0)

    Returns:
        outs (list): list of lists of str stdout lines
        errs (list): list of lists of str stderr lines
    """
    outs = []
    errs = []
    for cmd in cmds:
        ssh_obj.log_str(cmd)
        code, out, err = ssh_obj.execute(cmd)
        outs.append(out)
        errs.append(err)
        assert code == exit_code, "\nstdout:" + str(outs) + "\nstderr:" + str(errs)
        time.sleep(timeout)
    return outs, errs


def execute_until_timeout(
    ssh_obj: ShellHandler, cmd: str, timeout: int = 10, exit_code: int = 0
) -> bool:
    """Execute cmd and check for exit code until timeout

    Args:
        ssh_obj:         ssh connection obj
        cmd (str):       a single command to run
        timeout (int):   optional timeout between cmds (default 10)
        exit_code (int): optional code to check for (default 0)

    Returns:
        True: cmd return exit code 0 before timeout
        False: cmd does not return exit code 0
    """
    ssh_obj.log_str(cmd)
    count = max(1, int(timeout))
    while count > 0:
        code, out, err = ssh_obj.execute(cmd)
        if code == exit_code:
            return True
        count -= 1
        time.sleep(1)
    print("\nstdout:" + str(out) + "\nstderr:" + str(err))
    return False


def wait_tmux_testpmd_ready(
    ssh_obj: ShellHandler, tmux_session: str, timeout: int
) -> bool:
    """Wait until the testpmd in a tmux session is ready

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        tmux_session (str): tmux session name
        timeout (int): how many seconds to wait

    Returns:
        bool: True if success; False otherwise
    """
    for i in range(timeout):
        time.sleep(1)
        cmd = [f"tmux capture-pane -pt {tmux_session}"]
        outs, errs = execute_and_assert(ssh_obj, cmd, 0)
        for line in outs[0]:
            if line.startswith("Press enter to exit") or line.startswith("testpmd>"):
                return True
    return False


def stop_testpmd_in_tmux(ssh_obj: ShellHandler, tmux_session: str) -> None:
    """Stop the testpmd in a tmux session

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        tmux_session (str): tmux session name
    """
    cmd = f"tmux send-keys -t {tmux_session} 'quit' ENTER"
    ssh_obj.log_str(cmd)
    ssh_obj.execute(cmd)
    time.sleep(1)
    assert stop_tmux(ssh_obj, tmux_session)


def get_isolated_cpus(ssh_obj: ShellHandler) -> list:
    """Return a list of the isolated CPUs

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        type (str): type of hugepage, 1G or 2M

    Returns:
        list: The list of isolated CPUs
    """
    cmd = ["cat /sys/devices/system/cpu/isolated"]
    outs, errs = execute_and_assert(ssh_obj, cmd, 0)
    isolated = outs[0][0]
    isolated_cores = isolated.split(",")
    isolated_list = []
    for core in isolated_cores:
        if "-" not in core:
            isolated_list.append(int(core))
        else:
            a, b = core.split("-")
            sub_list = list(range(int(a), int(b) + 1))
            isolated_list.extend(sub_list)

    return isolated_list


def page_in_kb(type: str) -> str:
    """convert "1G" or "2M" to page size in KB

    Args:
        type (str): "1G" or "2M"

    Returns:
        str: page size in KB
    """
    type_to_kb = {"2M": "2048", "1G": "1048576"}
    if type not in type_to_kb:
        raise Exception(f"Unsupported hugepage type {type}")
    return type_to_kb[type]


def get_hugepage_info(ssh_obj: ShellHandler, type: str) -> Tuple[int, int]:
    """Get hugepage info

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        type (str): type of hugepage, 1G or 2M

    Returns:
        Tuple[int, int, int]: total pages, free pages
    """
    kb = page_in_kb(type)
    cmd = [
        f"cat /sys/kernel/mm/hugepages/hugepages-{kb}kB/nr_hugepages",
        f"cat /sys/kernel/mm/hugepages/hugepages-{kb}kB/free_hugepages",
    ]
    out, _ = execute_and_assert(ssh_obj, cmd, 0)
    return int(out[0][0]), int(out[1][0])


def allocate_hugepages(ssh_obj: ShellHandler, type: str, count: int):
    """Allocate hugepages

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        type (str): type of hugepage, 1G or 2M
        count (int): number of hugepage to allocate
    """
    kb = page_in_kb(type)

    cmd = [
        "awk '/MemFree:/{print $2}' /proc/meminfo",
    ]
    out, _ = execute_and_assert(ssh_obj, cmd, 0)
    free_kb = int(out[0][0])

    # To be safe, let's not allocate more than half of the free memory to hugepages
    if 2 * count * int(kb) > free_kb:
        raise Exception("Too many hugepages allocation not allowed")

    cmd = [
        f"echo {count} > /sys/kernel/mm/hugepages/hugepages-{kb}kB/nr_hugepages",
        f"mkdir -p /dev/pagesize-{type}",
        f"umount /dev/pagesize-{type} || true",
        f"mount -t hugetlbfs -o pagesize={type} none /dev/pagesize-{type}",
    ]
    execute_and_assert(ssh_obj, cmd, 0)


def calc_required_pages_2M(ssh_obj: ShellHandler, testpmd_instance: int) -> int:
    """_summary_

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        testpmd_instance (int): number of testpmd instances to support

    Returns:
        int: number of 2M pages required, 0 means existing pages are sufficient
    """
    _, free_1G = get_hugepage_info(ssh_obj, "1G")
    # For 1GB hugepage size, each free page support 1 testpmd instance
    if free_1G >= testpmd_instance:
        # Existing 1GB free page is sufficient
        return 0
    # Each extra instance requires 200 2M size page
    num_page_2M = 200 * (testpmd_instance - free_1G)

    total_2M, free_2M = get_hugepage_info(ssh_obj, "2M")
    if free_2M >= num_page_2M:
        # Existing 2MB free page is sufficient
        return 0

    # In addition to the currently used 2M pages
    num_page_2M += total_2M - free_2M
    return num_page_2M


def setup_hugepages(ssh_obj: ShellHandler, testpmd_instance: int) -> None:
    """setup hugepages to support the testpmd instances

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        testpmd_instance (int): number of testpmd instances to support
    """
    pages = calc_required_pages_2M(ssh_obj, testpmd_instance)
    if pages > 0:
        allocate_hugepages(ssh_obj, "2M", pages)


def delete_ipv6_neighbor(ssh_obj: ShellHandler, ipv6: str):
    """Delete IPv6 neighbor entry

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        ipv6 (str): IPv6 address
    """
    cmd = [f"ip -6 neigh show | awk '/{ipv6}/{{print $3}}'"]
    outs, _ = execute_and_assert(ssh_obj, cmd, 0)
    try:
        intf = outs[0][0].strip()
        if intf == "":
            return
    except IndexError:
        # empty outs, do nothing
        return
    cmd = [f"ip -6 neigh del {ipv6} dev {intf}"]
    execute_and_assert(ssh_obj, cmd, 0)


def switch_detected(ssh_obj: ShellHandler, interface: str) -> bool:
    """Test if the specified interface is connected to a switch

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        interface (str): interface name

    Returns:
        bool: True is a switch is detected
    """
    cmd = f"timeout 3 tcpdump -i {interface} -c 1 stp"
    ssh_obj.log_str(cmd)
    code, _, _ = ssh_obj.execute(cmd)
    return code == 0


def is_package_installed(ssh_obj: ShellHandler, package_name: str) -> bool:
    """Test if the specified RPM package is installed

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        package_name (str): RPM package name

    Returns:
        bool: True if the package is installed
    """
    cmd = f"rpm -q {package_name}"
    ssh_obj.log_str(cmd)
    code, _, _ = ssh_obj.execute(cmd)
    return code == 0


def get_nic_model(ssh_obj: ShellHandler, pf: str) -> str:
    """Get the NIC model

    Args:
        ssh_obj (ShellHandler): ssh connection obj
        pf (str): interface name

    Returns:
        str: The model of the NIC
    """
    cmd = [f"lshw -C network -businfo | grep {pf}"]
    outs, _ = execute_and_assert(ssh_obj, cmd, 0)
    return re.split("\\s{2,}", outs[0][0])[-1].strip()
