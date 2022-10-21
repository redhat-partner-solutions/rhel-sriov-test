## Test Case Name: SR-IOV.macAddress.DPDK
# UUID: d786bfca-219c-4b9f-ad9b-59fa1bc8cbba

### Objective(s): Test and ensure that VF (virtual function) MAC address functions as intended when bound to the DPDK driver.

### Test procedure

* On DUT, create 1 VF and assign a mac address. Assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF} vf 0 mac ${DUT_VF0_MAC}
```

* Bind the VF 0 pci address to vfio-pci driver. Assert on 0 exit code of each of the following steps,
```
modprobe vfio-pci
echo ${DUT_VF0_PCI} > /sys/bus/pci/devices/${DUT_VF0_PCI}/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/${DUT_VF0_PCI}/driver_override
echo ${DUT_VF0_PCI} > /sys/bus/pci/drivers/vfio-pci/bind
```

* Start a testpmd instance with the VF 0 pci address, put testpmd in icmpecho mode, for example:
```
podman run -it --rm --privileged -v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules --cpuset-cpus 30,32,34 docker.io/patrickkutch/dpdk:v21.11 dpdk-testpmd -l 30,32,34 -n 4 -a ${DUT_VF0_PCI} -- --nb-cores=2 -i
testpmd> set fwd icmpecho
testpmd> start
```

* On trafficgen, add ip address and arp entry,
```
ip addr add ${TGEN_IP}/24 dev ${TGEN_PF}
arp -s ${DUT_IP} ${DUT_VF0_MAC}
```

* On trafficgen: assert on ping exit code 0
```
ping -W 1 -c 1 ${DUT_IP}
```

* On trafficgen, remove arp entry and ip address,
```
arp -d ${DUT_IP}
ip addr del ${TGEN_IP}/24 dev ${TGEN_PF}
```

* stop testpmd,
```
testpmd> quit
```

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
