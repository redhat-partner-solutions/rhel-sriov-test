# Test Case Name: SR-IOV.MultipleVFCreation.withMAC.DPDK

### Objective(s): A robustness test to ensure that, from a clean start, VFs (virtual functions) provision MAC address functions with DPDK

### Test procedure

* Reset the VFs
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```

* Ensure the reset succeeds (or check no VF exists under the ```$PF``` by ensuring ```sriov_numvfs``` is 0

* Create the maximum number of VFs allowed by ```$PF```, wait up to 10 seconds for all VFs to be created
```
modprobe vfio-pci
total_vfs = $(cat /sys/class/net/$PF/device/sriov_totalvfs)
echo ${total_vfs} > /sys/class/net/$PF/device/sriov_numvfs
```

* Set the MAC address for each VF; bind each VF to vfio-pci: each of the following bind/unbind operations should complete within 1 second
```
for i in $(seq total_vfs); do
    ip link set ${PF} vf $i mac $((DUT_MAC_base+i))
    echo ${DUT_VFn_PCI} > /sys/bus/pci/devices/${DUT_VFn_PCI}/driver/unbind
    echo vfio-pci > /sys/bus/pci/devices/${DUT_VFn_PCI}/driver_override
    echo ${DUT_VFn_PCI} > /sys/bus/pci/drivers/vfio-pci/bind
done
```

### Clean up
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```
