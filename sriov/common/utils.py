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
    cmd = f"arp -d {ip} || true"
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    
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
        vf_id (str):      virtual function ID

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
    if not vfs_created(ssh_obj, pf_interface, num_vfs, timeout):
        raise Exception(f"Failed to create {num_vfs} VFs on {pf_interface}")

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
        code, out, err = ssh_obj.execute(check_vfs)
        if code != 0:
            time.sleep(1)
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
