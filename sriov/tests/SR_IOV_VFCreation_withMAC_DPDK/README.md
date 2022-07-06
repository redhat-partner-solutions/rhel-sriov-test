# Test Case Name: SR-IOV.VFCreation.withMAC.DPDK

### Objective(s): A robustness test to ensure that, from a clean start, the VF (virtual function) provisioning of MAC addresses works with DPDK

### Test procedure

* Reset the VFs and create 1 VF, assert exit code == 0 on each of the following steps
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
echo 1 > /sys/class/net/$PF/device/sriov_numvfs
ip link set ${PF} vf 0 mac ${DUT_VF0_MAC}
ip link set ${PF} vf 0 spoof on
ip link set ${PF} vf 0 trust on
ip link set ${PF} vf 0 max_tx_rate 10
ip link set ${PF} vf 0 vlan 10 qos 5
```

* Bind VF 0 to vfio-pci, assert exit code == 0 on each of the following steps
```
modprobe vfio-pci
echo ${DUT_VF0_PCI} > /sys/bus/pci/devices/${DUT_VF0_PCI}/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/${DUT_VF0_PCI}/driver_override
echo ${DUT_VF0_PCI} > /sys/bus/pci/drivers/vfio-pci/bind
```

* Read the MAC address of VF 0 and assert it == ```${DUT_VF0_MAC}```
```
ip link show ens7f3 | awk '/vf 0/{print $4;}'
```

* Run the clean up

* Repeat the test 100 times

### Clean up
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```
