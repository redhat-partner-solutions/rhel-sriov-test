
## Test Case Name: SR-IOV.Permutation
# UUID: 52d5e6ca-8a98-4151-9b2e-7a2946073325

### Objective(s): Test VFs (virtual function) bound to DPDK driver with different properties combined

### Test procedure

* On DUT, create 1 VF; set VF 0 with a permutation of the following permutations,

| Spoofchk (on/off) | Trust(on/off) | vlan(with/without) | QoS (with/without) | max_tx_rate (with/without) |
| --- | --- | --- | --- | --- |

assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/{DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/{DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF} vf 0 mac ${DUT_VF0_MAC}
ip link set ${DUT_PF} vf 0 spoof ${spoof}
ip link set ${DUT_PF} vf 0 trust ${trust}
# next line only if vlan is set
ip link set ${DUT_PF} vf 0 vlan ${vlan} qos ${qos}
# next line only if max_tx_rate is set
ip link set ${DUT_PF} vf 0 max_tx_rate ${max_tx_rate}
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

* On trafficgen,
```
ip addr add ${TGEN_IP}/24 dev ${TGEN_PF}
arp -s ${DUT_IP} ${DUT_VF0_MAC}
```

* On trafficgen: assert on ping exit code 0
```
ping -W 1 -c 1 ${DUT_IP}
```

* On trafficgen, stop testpmd,
```
testpmd> quit
```

* Repeat test with next permutation

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
