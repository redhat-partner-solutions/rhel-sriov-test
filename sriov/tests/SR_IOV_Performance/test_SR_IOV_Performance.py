from sriov.common.utils import (
    execute_and_assert,
    execute_until_timeout,
    create_vfs,
    set_pipefail,
    get_pci_address,
    bind_driver,
    get_isolated_cpus_numa,
    get_hugepage_info,
)
import json


# Use pytest --iteration to adjust the execution_number parameter for desired amount
# of repeated tests
def test_SRIOVPerformance(dut, trafficgen, settings, testdata, execution_number):
    """Test and ensure that VFs provision with MTU functions as intended

    Args:
        dut:              ssh connection obj
        settings:         settings obj
        testdata:         testdata obj
        execution_number: execution_number parameter
    """
    pfs = list(testdata.pfs.keys())
    dut_vfs_pci = [settings.config["dut"]["interface"]["vf1"]["pci"], settings.config["dut"]["interface"]["vf2"]["pci"]]

    assert set_pipefail(dut)

    # Check trafficgen ports are on the same numa node
    trafficgen_pfs = [settings.config["trafficgen"]["interface"]["pf1"]["name"], settings.config["trafficgen"]["interface"]["pf2"]["name"]]
    trafficgen_pfs_pci = [settings.config["trafficgen"]["interface"]["pf1"]["pci"], settings.config["trafficgen"]["interface"]["pf2"]["pci"]]
    print(settings.config["trafficgen"])
    trafficgen_vfs_pci = [settings.config["trafficgen"]["interface"]["vf1"]["pci"], settings.config["trafficgen"]["interface"]["vf2"]["pci"]]
    print(trafficgen_vfs_pci)
    steps = []
    for pf_pci in trafficgen_pfs_pci:
        steps.append(f"cat /sys/bus/pci/devices/{pf_pci}/numa_node")
    outs, errs = execute_and_assert(trafficgen, steps, 0)
    
    if outs[0][0] != outs[1][0]:
        assert False, "Trafficgen PFs are on different numa nodes"
    else:
        trafficgen_numa = int(outs[0][0])

    total_1G, free_1G = get_hugepage_info(trafficgen, "1G")
    if free_1G < 2:
        # Existing 1G free page is sufficient
        assert False, "Trafficgen 1G hugepages insufficient (2 minimum)"
    
    # Check dut ports are on the same numa node
    dut_pfs_pci = [settings.config["dut"]["interface"]["pf1"]["pci"], settings.config["dut"]["interface"]["pf2"]["pci"]]
    steps = []
    for pf_pci in dut_pfs_pci:
        steps.append(f"cat /sys/bus/pci/devices/{pf_pci}/numa_node")
    outs, errs = execute_and_assert(dut, steps, 0)
    
    if outs[0][0] != outs[1][0]:
        assert False, "DUT PFs are on different numa nodes"
    else:
        dut_numa = int(outs[0][0])
    print(outs[0][0])

    total_1G, free_1G = get_hugepage_info(dut, "1G")
    if free_1G < 2:
        # Existing 1G free page is sufficient
        assert False, "DUT 1G hugepages insufficient (2 minimum)"

    # Get isolated CPUS
    trafficgen_cpus = get_isolated_cpus_numa(trafficgen, trafficgen_numa)
    print(trafficgen_cpus)
    dut_cpus = get_isolated_cpus_numa(dut, dut_numa)
    print(dut_cpus)

    if len(trafficgen_cpus) < 7:
        assert False, f"Not enough isolated CPUs (7) on trafficgen numa node {trafficgen_numa}"
    else:
        trafficgen_cpus = trafficgen_cpus[0:7]
    
    if len(dut_cpus) < 3:
        assert False, f"Not enough isolated CPUs (3) on testpmd numa {dut_numa}"
    else:
        dut_cpus = dut_cpus[0:3]
        print(dut_cpus)

    # Spoof off, trust on for dut
    steps = ["modprobe vfio-pci"]
    for pf in pfs:
        # Create the 2 VFs
        assert create_vfs(dut, testdata.pfs[pf]["name"], 1)

        steps.append(f"ip link set {testdata.pfs[pf]['name']}v0 down")
        steps.append(f"ip link set {testdata.pfs[pf]['name']} vf 0 spoof off")
        steps.append(f"ip link set {testdata.pfs[pf]['name']} vf 0 trust on")

    execute_and_assert(dut, steps, 0)

    # Spoof off, trust on for trafficgen
    steps = ["modprobe vfio-pci"]
    
    execute_and_assert(trafficgen, steps, 0)

    # Bind testpmd VFs to vfio-pci
    for pf in pfs:
        pci_pf_vf0 = get_pci_address(dut, testdata.pfs[pf]['name'] + "v0")
        assert bind_driver(dut, pci_pf_vf0, "vfio-pci")
    
    # Bind trafficgen PFs to vfio-pci
    for pf in trafficgen_pfs_pci:
        assert bind_driver(trafficgen, pf, "vfio-pci")

    # Start the testpmd auto
    dut_cpus_string = ""
    for cpu in dut_cpus:
        dut_cpus_string += str(cpu) + ","
    dut_cpus_string = dut_cpus_string[:-1]
    testpmd_cmd = [f"{settings.config['container_manager']} run -d --rm --privileged -p {settings.config['testpmd_port']}:{settings.config['testpmd_port']} -v /dev/hugepages:/dev/hugepages -v /sys/bus/pci/devices:/sys/bus/pci/devices -v /lib/firmware:/lib/firmware --cpuset-cpus {dut_cpus_string} {settings.config['testpmd_img']} --pci {dut_vfs_pci[0]} --pci {dut_vfs_pci[1]} --http-port {settings.config['testpmd_port']} --auto"]
    outs, errs = execute_and_assert(dut, testpmd_cmd, 0)
    testpmd_id = outs[0][0]

    # Check testpmd is running
    cmd = f"curl localhost:{settings.config['testpmd_port']}/testpmd/status"
    assert execute_until_timeout(dut, cmd)

    # Start trafficgen
    trafficgen_cpus_string = ""
    for cpu in trafficgen_cpus:
        trafficgen_cpus_string += str(cpu) + ","
    trafficgen_cpus_string = trafficgen_cpus_string[:-1]
    trafficgen_cmd = [f"{settings.config['container_manager']} run -d --rm --privileged -p {settings.config['trafficgen_port']}:{settings.config['trafficgen_port']} -v /dev:/dev -v /sys:/sys -v /lib/modules:/lib/modules --cpuset-cpus {trafficgen_cpus_string} -e pci_list={trafficgen_pfs_pci[0]},{trafficgen_pfs_pci[1]} --ip={settings.config['trafficgen_ip']} {settings.config['trafficgen_img']}"]
    outs, errs = execute_and_assert(trafficgen, trafficgen_cmd, 0)
    trafficgen_id = outs[0][0]

    client_cmd = [f"wget -O /tmp/client.py https://raw.githubusercontent.com/redhat-eets/netgauge/main/rfc2544/client.py"]
    outs, errs = execute_and_assert(trafficgen, client_cmd, 0)

    client_cmd = f"python3 /tmp/client.py status --server-addr {settings.config['trafficgen_ip']} --server-port {settings.config['trafficgen_port']}"
    assert execute_until_timeout(trafficgen, client_cmd)

    client_cmd = [f"python3 /tmp/client.py auto --server-addr {settings.config['trafficgen_ip']} --server-port {settings.config['trafficgen_port']}"]
    outs, errs = execute_and_assert(trafficgen, client_cmd, 0, cmd_timeout=60*settings.config['trafficgen_timeout'])
    results = json.loads(outs[0][0])

    # Clean up (delete containers, delete VFs, bind to kernel driver)
    kill_testpmd = [f"{settings.config['container_manager']} kill {testpmd_id}"]
    execute_and_assert(dut, kill_testpmd, 0)

    kill_trafficgen = [f"{settings.config['container_manager']} kill {trafficgen_id}"]
    execute_and_assert(trafficgen, kill_trafficgen, 0)

    for pf in trafficgen_pfs_pci:
        assert bind_driver(trafficgen, pf, "i40e")

    # Compare trafficgen results to config
    assert results['0']['rx_l1_bps'] >= settings.config['trafficgen_rx_bps_limit']