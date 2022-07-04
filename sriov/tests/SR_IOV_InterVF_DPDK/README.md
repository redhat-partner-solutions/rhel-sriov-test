
## Test Case Name: SR-IOV.InterVF.DPDK

### Objective(s): Test and ensure that VFs (virtual function) bound to DPDK driver can communicate with VF on the same PF.

### Test procedure

* On DUT, Create two VF,
```
echo 0 > /sys/class/net/{pf}/device/sriov_numvfs
echo 2 > /sys/class/net/{pf}/device/sriov_numvfs
```

* On DUT, set up the VF with a permutation; assert on 0 exit code of each permutation setup

| Spoofchk (on/off) | Trust(on/off) | vlan(with/without) | QoS (with/without) | max_tx_rate (with/without) |
| --- | --- | --- | --- | --- |

* Bind the VF 0 to vfio-pci
```
modprobe vfio-pci
echo ${DUT_VF0_PCI} > /sys/bus/pci/devices/${DUT_VF0_PCI}/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/${DUT_VF0_PCI}/driver_override
echo ${DUT_VF0_PCI} > /sys/bus/pci/drivers/vfio-pci/bind
```

* Start testpmd on VF 0 in icmpecho mode, example,
```
podman run -it --rm --privileged -v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules --cpuset-cpus 30,32,34 docker.io/patrickkutch/dpdk:v21.11 dpdk-testpmd -l 30,32,34 -n 4 -a ${DUT_VF0_PCI} -- --nb-cores=2 --forward=icmpecho
```

* Set up ip address on VF 1 interface; set up an arp entry with VF 0 address; send ping; remove the ip address and arp entry after ping; assert on 0 exit code of each of the following steps,
```
ip link set ${PF}v1 up
ip add add ${DUT_IP_1}/24 dev ${PF}v1
arp -s ${DUT_IP_0} ${DUT_VF0_MAC}
ping ${DUT_IP_0}/24
arp -d ${DUT_IP_0}
ip addr del ${DUT_IP_1}/24 dev ${PF}v1
```

* stop testpmd,
```
testpmd> quit
```

* Repeat test with next permutation

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```



