import time 

def get_pci_address(ssh_obj, iface):
    """ Get the PCI address of an interface

    Args:
        ssh_obj:     ssh_obj to the remote host
        iface (str): interface name, example: "ens2f0"
    
    Returns: 
        PCI address, example "0000:17:00.0"
    
    Raises:
        Exception: command failure
    """
    cmd = "ethtool -i {}".format(iface) +" | awk '/bus-info:/{print $2;}'"
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    return out[0].strip("\n")

def bind_driver(ssh_obj, pci, driver):
    """ Bind the PCI address to the driver

    Args:
        ssh_obj:      ssh_obj to the remote host
        pci (str):    PCI address, example "0000:17:00.0"
        driver (str): driver name, example "vfio-pci"
    
    Returns: 
        True: on success of binding
    
    Raises:
        Exception: command failure
    """
    device_path = "/sys/bus/pci/devices/" + pci
    steps = ["modprobe {}".format(driver),
             "echo {} > {}/driver/unbind".format(pci, device_path),
             "echo {} > {}/driver_override".format(driver, device_path),
             "echo {} > /sys/bus/pci/drivers/{}/bind".format(pci, driver)
            ]
    for step in steps:
        print(step)
        code, out, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
    return True    

def config_interface(ssh_obj, intf, vlan, ip):
    """ Config an IP address on VLAN interface; if VLAN is 0, config IP on 
        main interface

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name
        vlan (str): VLAN ID
        ip (str):   IP address

    Raises:
        Exception: command failure
    """
    if vlan != 0:
        steps = [f"ip link add link {intf} name {intf}.{vlan} type vlan id {vlan}",
                 f"ip add add {ip}/24 dev {intf}.{vlan}",
                 f"ip link set {intf}.{vlan} up"
                ]
    else:
        steps = [f"ip add add {ip}/24 dev {intf}"]
    for step in steps:
        print(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)
        
def clear_interface(ssh_obj, intf, vlan=0):
    """ Clear the IP address from the VLAN interface and the main interface

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name
        vlan (str): VLAN ID

    Raises:
        Exception: command failure
    """
    # The virtual interface may not exist, force true to ignore the command failure
    if vlan != 0:
        steps = [
                f"ip addr flush dev {intf}.{vlan} || true",
                f"ip link del {intf}.{vlan} || true",
                f"ip addr flush dev {intf} || true"
                ]
    else:
        steps = [f"ip addr flush dev {intf} || true"]
    for step in steps:
        print(step)
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)

def add_arp_entry(ssh_obj, ip, mac):
    """ Add a static ARP entry

    Args:
        ssh_obj:   SSH connection obj
        ip (str):  IP address
        mac (str): MAC address

    Raises:
        Exception: command failure
    """
    cmd = f"arp -s {ip} {mac}"
    print(cmd)
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    
def rm_arp_entry(ssh_obj, ip):
    """ Remove a static ARP entry

    Args:
        ssh_obj:  SSH connection obj
        ip (str): IP address

    Raises:
        Exception: command failure
    """
    cmd = f"arp -d {ip} || true"    # not a failure if the ip entry not exist
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)

def prepare_ping_test(tgen, tgen_intf, tgen_vlan, tgen_ip, tgen_mac, 
                      dut, dut_ip, dut_mac,
                      testdata):
    """Collection of steps to prepare for ping test
    
    Args:
        tgen (object): trafficgen ssh handler
        tgen_intf (str): trafficgen physical interface name
        tgen_vlan (int): vlan ID on the trafficgen physical interface
        tgen_ip (str): trafficgen ip address
        tgen_mac (str): trafficgen mac address; set to None will not add arp entry on DUT
        dut (object): DUT ssh handler
        dut_ip (str): DUT ip address
        dut_mac (str): DUT mac address
        testdata (object): testdata object
    """
    clear_interface(tgen, tgen_intf, tgen_vlan)
    
    #track if ping is executed when cleanup_after_ping is called for cleanup
    testdata['ping']['run'] = True
    testdata['ping']['tgen_intf'] = tgen_intf
    testdata['ping']['tgen_vlan'] = tgen_vlan
    testdata['ping']['tgen_ip'] = tgen_ip
    testdata['ping']['tgen_mac'] = tgen_mac
    testdata['ping']['dut_ip'] = dut_ip
    testdata['ping']['dut_mac'] = dut_mac
    
    config_interface(tgen, tgen_intf, tgen_vlan, tgen_ip)
    add_arp_entry(tgen, dut_ip, dut_mac)
    if tgen_mac is not None:
        add_arp_entry(dut, tgen_ip, tgen_mac)
    
def cleanup_after_ping(tgen, dut, testdata):
    """Collection of steps to cleanup after ping test
    
    Args:
        tgen (object): trafficgen ssh handler
        dut (object): DUT ssh handler
        testdata (object): testdata object
    """
    run = testdata['ping'].get('run', False)
    if run:
        tgen_intf = testdata['ping'].get('tgen_intf')
        tgen_vlan= testdata['ping'].get('tgen_vlan')
        tgen_ip = testdata['ping'].get('tgen_ip')
        dut_ip = testdata['ping'].get('dut_ip')
        tgen_mac = testdata['ping']['tgen_mac']
        rm_arp_entry(tgen, dut_ip)
        clear_interface(tgen, tgen_intf, tgen_vlan)
        if tgen_mac is not None:
            rm_arp_entry(dut, tgen_ip)

def set_mtu(tgen, tgen_pf, dut, dut_pf, dut_vf, mtu, testdata):
    """set MTU on trafficgen and DUT

    Args:
        tgen (object): trafficgen ssh connection
        tgen_pf (str): trafficgen PF
        dut (object): DUT ssh connection
        dut_pf (str): DUT PF
        dut_vf (int): DUT VF id
        mtu (int): MTU size in bytes
        testdata (object): testdata object
    """
    testdata['mtu']['changed'] = True
    testdata['mtu']['tgen_intf'] = tgen_pf
    testdata['mtu']['du_intf'] = dut_pf
    testdata['mtu']['dut_vf'] = dut_vf
    
    steps = [f"ip link set {tgen_pf} mtu {mtu}"]
    execute_and_assert(tgen, steps, 0)
    
    steps = [
        f"ip link set {dut_pf} mtu {mtu}",
        f"ip link set {dut_pf}v{dut_vf} mtu {mtu}",
    ]
    execute_and_assert(dut, steps, 0, timeout=0.1)

def reset_mtu(tgen, dut, testdata):
    """reset MTU on trafficgen and DUT

    Args:
        tgen (object): trafficgen ssh connection
        dut (object): DUT ssh connection
        testdata (object): testdata object
    """
    changed = testdata['mtu'].get('changed', False)
    if changed:
        tgen_intf = testdata['mtu'].get('tgen_intf')
        du_intf = testdata['mtu'].get('du_intf')
        tgen.execute(f"ip link set {tgen_intf} mtu 1500")
        dut.execute(f"ip link set {du_intf} mtu 1500")
                 
def start_tmux(ssh_obj, name, cmd):
    """ Run cmd in a tmux session

    Args:
        ssh_obj:    SSH connection obj
        name (str): tmux session name
        cmd (str):  a single command to run

    Raises:
        Exception: command failure
    """
    
    steps = [
            f"tmux kill-session -t {name} || true",
            f"tmux new-session -s {name} -d {cmd}"
            ]
    
    for step in steps:
        code, _, err = ssh_obj.execute(step)
        if code != 0:
            raise Exception(err)

def stop_tmux(ssh_obj, name):
    """ Stop tmux session

    Args:
        ssh_obj:    SSH connection obj
        name (str): tmux session name

    Raises:
        Exception: command failure
    """
    code, _, err = ssh_obj.execute(f"tmux kill-session -t {name} || true")
    if code != 0:
        raise Exception(err)

def get_intf_mac(ssh_obj, intf):
    """ Get the MAC address from the interface name

    Args:
        ssh_obj:    SSH connection obj
        intf (str): interface name

    Raises:
        Exception:  command failure
        ValueError: failure in parsing
    """
    cmd = f"cat /sys/class/net/{intf}/address"
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    for line in out:
        if len(line.split(":")) == 6:
            return line.strip("\n")
    raise ValueError("can't parse mac address")

def get_vf_mac(ssh_obj, intf, vf_id):
    """ Get the MAC address from the interface's VF ID

    Args:
        ssh_obj (_type_): SSH connection obj
        intf (str):       interface name
        vf_id (int):      virtual function ID

    Raises:
        Exception:  command failure
        ValueError: failure in parsing
    """
    cmd = f"ip link show {intf} | awk '/vf {vf_id}/" + "{print $4;}'"
    print(cmd)
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    for line in out:
        if len(line.split(":")) == 6:
            return line.strip("\n")
    raise ValueError("can't parse mac address")

def set_vf_mac(ssh_obj, intf, vf_id, address, timeout = 10, interval = 0.1):
    """ Set the VF mac address
    
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
    print(set_mac_cmd)
    code, out, err = ssh_obj.execute(set_mac_cmd)
    if code != 0:
        return False 

    count = int(timeout/interval) + 1
    while count > 0:
        vf_mac = get_intf_mac(ssh_obj, f"{intf}v{vf_id}")
        if vf_mac == address:
            return True
        count -= 1
        time.sleep(interval)    
    return False

def verify_vf_address(ssh_obj, intf, vf_id, address, timeout = 10, interval = 0.1):
    """ verify that the VF has the specified address
    
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
    count = int(timeout/interval) + 1
    while count > 0:
        vf_mac = get_vf_mac(ssh_obj, intf, vf_id)
        print(vf_mac)
        if vf_mac == address:
            return True
        count -= 1
        time.sleep(interval)
    return False
  
def vfs_created(ssh_obj, pf_interface, num_vfs, timeout = 10):
    """ Check that the num_vfs of pf_interface are created before timeout
    
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
    print(cmd)
    for i in range(timeout):
        time.sleep(1)     
        code, out, err = ssh_obj.execute(cmd)
        if code != 0:
            continue
        if int(out[0].strip()) == num_vfs:
            return True
    return False

def create_vfs(ssh_obj, pf_interface, num_vfs, timeout = 10):
    """ Create the num_vfs of pf_interface
    
    Args:
        ssh_obj:            ssh connection obj
        pf_interface (str): name of the PF
        num_vfs (int):      number of VFs to create under PF
        timout (int):       times to check for VFs (default 10)
    
    Raises:
        Exception:  failed to create VFs before timeout exceeded
    """
    clear_vfs = f"echo 0 > /sys/class/net/{pf_interface}/device/sriov_numvfs"
    print(clear_vfs)
    ssh_obj.execute(clear_vfs, 60)
    create_vfs = f"echo {num_vfs} > /sys/class/net/{pf_interface}/device/sriov_numvfs"
    print(create_vfs)
    ssh_obj.execute(create_vfs, 60)
    return vfs_created(ssh_obj, pf_interface, num_vfs, timeout)

def no_zero_macs_pf(ssh_obj, pf_interface, timeout = 10):
    """ Check that none of the pf_interface VFs have all zero MAC addresses (from the pf report)

    Args:
        ssh_obj:            ssh connection obj
        pf_interface (str): name of the PF
        timout (int):       times to check for VFs (default 10)

    Returns:
        True: no interfaces have all zero MAC addresses
        False: an interface with zero MAC address was found or timeout exceeded
    """
    check_vfs = "ip -d link show " + pf_interface
    print(check_vfs)
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

def no_zero_macs_vf(ssh_obj, pf_interface, num_vfs, timeout = 10):
    """ Check that none of the interfaces's VFs have zero MAC addresses (from the vf reports)

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

def set_pipefail(ssh_obj):
    """ Set the pipefail to persist errors

    Args:
        ssh_obj: ssh connection obj

    Raises:
        Exception: command failure
    """
    set_command = "set -o pipefail"
    code, out, err = ssh_obj.execute(set_command)
    if code != 0:
        raise Exception(err)

def execute_and_assert(ssh_obj, cmds, exit_code, timeout=0):
    """ Execute the list of commands, assert exit code, and return stdouts and stderrs 

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
        print(cmd)
        code, out, err = ssh_obj.execute(cmd)
        outs.append(out)
        errs.append(err)
        assert code == exit_code
        time.sleep(timeout)
    return outs, errs

def execute_until_timeout(ssh_obj, cmd, timeout=10):
    """ Execute cmd and check for 0 exit code until timeout

    Args:
        ssh_obj:         ssh connection obj
        cmd (str):       a single command to run
        timeout (int):   optional timeout between cmds (default 10)

    Returns:
        True: cmd return exit code 0 before timeout
        False: cmd does not return exit code 0
    """
    count = max(1, int(timeout))
    while count > 0:
        code, out, err = ssh_obj.execute(cmd)
        if code == 0:
            return True
        count -= 1
        time.sleep(1)
    return False