import time 

def get_pci_address(ssh_obj, iface):
    """
    :param ssh_obj: ssh_obj to the remote host
    :param iface: interface name, example: "ens2f0"
    :return: pci address, example "0000:17:00.0"
    """
    cmd = "ethtool -i {}".format(iface) +" | awk '/bus-info:/{print $2;}'"
    code, out, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    return out[0].strip("\n")

def bind_driver(ssh_obj, pci, driver):
    """
    :param ssh_obj: ssh_obj to the remote host
    :param pci: pci address, example "0000:17:00.0"
    :param driver: driver name, example "vfio-pci"
    :return: True on success
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
            return False
    return True    

def config_interface(ssh_obj, intf, vlan, ip):
    """config an ip address on vlan interface; if vlan is 0, config ip on main interface

    Args:
        ssh_obj: ssh connection obj
        intf (str): interface name
        vlan (str): vlan id
        ip (str): ip address

    Raises:
        Exception: stderr msg in array
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
    """clear the ip address from the vlan interface and the main interface

    Args:
        ssh_obj: ssh connection obj
        intf (str): interface name
        vlan (str): vlan id

    Raises:
        Exception: stderr msg in array
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
    """    add static arp entry

    Args:
        ssh_obj: ssh connection obj
        ip: ip address
        mac: mac address

    Raises:
        Exception: stderr msg in array
    """
    cmd = f"arp -s {ip} {mac}"
    print(cmd)
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    
def rm_arp_entry(ssh_obj, ip):
    """remove an static arp entry

    Args:
        ssh_obj: ssh connection obj
        ip: ip address

    Raises:
        Exception: stderr msg in array
    """
    cmd = f"arp -d {ip} || true"
    code, _, err = ssh_obj.execute(cmd)
    if code != 0:
        raise Exception(err)
    
def start_tmux(ssh_obj, name, cmd):
    """Run cmd in a tmux session

    Args:
        ssh_obj: ssh connection obj
        name: tmux session name
        cmd (str): a single command to run
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
    """stop tmux session

    Args:
        ssh_obj: ssh connection obj
        name (str): tmux session name
    """
    code, _, err = ssh_obj.execute(f"tmux kill-session -t {name} || true")
    if code != 0:
        raise Exception(err)

def get_intf_mac(ssh_obj, intf):
    """get mac address from the interface name

    Args:
        ssh_obj (_type_): ssh connection obj
        intf (str): interface name
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
    ''' Check that the num_vfs of pf_interface are created before timeout
    
    Args:
        ssh_obj: ssh connection obj
        pf_interface: name of the PF
        num_vfs: number of VFs to check under PF
        timout (optional): times to check for VFs (default 10)
    Returns:
        True if all VFs are created, throws RuntimeError otherwise
    '''
    cmd = "ls -d /sys/class/net/" + pf_interface + "v* | wc -w"
    for i in range(timeout):
        code, out, err = ssh_obj.execute(cmd)
        if code != 0:
            raise Exception(err)
        if int(out[0].strip()) == int(num_vfs):
            return True
        time.sleep(1)
    raise RuntimeError("VFs not created before timeout")

def no_zero_macs(ssh_obj, pf_interface, timeout = 10):
    ''' Check that none of the pf_interface VFs have all zero MAC addresses

    Args:
        ssh_obj: ssh connection obj
        pf_interface: name of the PF
        timout (optional): times to check for VFs (default 10)

    Returns:
        True if no interfaces have all zero MAC addresses, throws RuntimeError otherwise
    '''
    check_vfs = "ip -d link show " + pf_interface
    for i in range(timeout):
        code, out, err = ssh_obj.execute(check_vfs)
        if code != 0:
            raise Exception(err)
        no_zeros = True
        for out_slice in out:
            if "00:00:00:00:00:00" in out_slice:
                no_zeros = False
                break
        if no_zeros:
            return True
        time.sleep(1)
    raise RuntimeError("Zero MAC addresses present during timeout")
