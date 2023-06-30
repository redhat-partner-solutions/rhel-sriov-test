# Test Case Name: SR-IOV.Performance

### Objective(s): A RFC2544 performance test to evaluate a system's (relative) performance when running DPDK workloads. This relies on a trafficgen client and containers built from [netgauge](https://github.com/redhat-eets/netgauge)

### Test procedure

* Reset the VFs
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```

* Ensure the reset succeeds (or check no VF exists under the ```$PF``` by ensuring ```sriov_numvfs``` is 0

* Ensure the trafficgen server ports are on the same numa node, repeat with the two testpmd server ports
```
cat /sys/bus/pci/devices/<pci_address>/numa_node
```

* Ensure the trafficgen server has 2 1GB hugepages, repeat with the testpmd server

* On the trafficgen, get 7 isolated CPUs from the numa node associated with the trafficgen ports, repeat on the testpmd server with 3 isolated CPUs

* On the testpmd server, create 1 VF on each PF, setting spoof checking off and trust mode on, and bind to vfio-pci
```
echo 1 > /sys/class/net/$PF/device/sriov_numvfs
ip link set $PF vf 0 spoof off
ip link set $PF vf 0 trust on
echo $VF_PCI > /sys/bus/pci/devices/$VF_PCI/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/$VF_PCI/driver_override
echo $VF_PCI > /sys/bus/pci/drivers/vfio-pci/bind
```

* On the trafficgen server, start the prebuilt testpmd container
```
podman run -d --rm --privileged -p $PORT:$PORT -v /dev/hugepages:/dev/hugepages -v /sys/bus/pci/devices:/sys/bus/pci/devices -v /lib/firmware:/lib/firmware --cpuset-cpus $CPUs $testpmd_container --pci $VF1 --pci $VF2 --http-port $PORT --auto
```

* On the testpmd server, ensure that testpmd has started using the REST API
```
curl localhost:$PORT/testpmd/status
```

* On the trafficgen, bind the 2 trafficgen PF ports to vfio-pci
```
echo $PF_PCI > /sys/bus/pci/devices/$PF_PCI/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/$PF_PCI/driver_override
echo $PF_PCI > /sys/bus/pci/drivers/vfio-pci/bind
```

* On the trafficgen, start the trafficgen container
```
podman run -d --rm --privileged -p $PORT:$PORT -v /dev:/dev -v /sys:/sys -v /lib/modules:/lib/modules --cpuset-cpus $CPUs -e pci_list=$PF1,$PF2 --ip=$IP $trafficgen_container
```

* On the trafficgen, start the client (once to stabilize, once to collect results)
```
python3 /tmp/client.py status --server-addr $IP --server-port $PORT
python3 /tmp/client.py start --server-addr $IP --server-port $PORT --timeout 60
python3 /tmp/client.py stop --server-addr $IP --server-port $PORT
python3 /tmp/client.py auto --server-addr $IP --server-port $PORT
```

* Compare the results bps to the baseline value

### Clean up
* Kill containers on testpmd and trafficgen

* Reset PF driver on trafficgen

* Remove VFs on testpmd
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```
