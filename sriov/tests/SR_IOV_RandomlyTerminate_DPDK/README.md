## Test Case Name: SR-IOV.RandomlyTerminate.DPDK

### Objective(s): A robustness test to ensure that randomly killed and restarted testpmd containers recover. Permutations are necessary for random termination and random termination with iavf binding.

### Test procedure

* Reset the VFs
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```

* Ensure the reset succeeds (or check no VF exists under the ```$PF``` by ensuring ```sriov_numvfs``` is 0)

* Bind the device driver (i.e. ice)

* Set hugepages
```
echo 2048 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
mkdir -p /mnt/huge
mount -t hugetlbfs nodev /mnt/huge
echo 8196 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages
echo 8196 > /sys/devices/system/node/node1/hugepages/hugepages-2048kB/nr_hugepages
```

* Kill all running containers

* Set the link up and create the number of VFs desired, wait up to 10 seconds for all VFs to be created
```
modprobe vfio-pci
ip link set $PF up
echo ${num_vfs} > /sys/class/net/$PF/device/sriov_numvfs
```

* Start pinging the dut from the trafficgen

* Start containers

* Randomly kill containers

* Rebind iavf, if required by permutation

* Restart containers, checking all are up and transmitting after restart


### Clean up
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```