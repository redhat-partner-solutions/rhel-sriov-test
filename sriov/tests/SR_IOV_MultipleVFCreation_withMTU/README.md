# Test Case Name: SR-IOV.MultipleVFCreation.withMTU

### Objective(s): A robustness test to ensure that, from a clean start, the maximum number of VFs (virtual functions) can be created and the maximum MTU (maximum transmission unit) configured for each VF

### Test procedure

* Reset the VFs
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
```

* Ensure the reset succeeds (or check no VF exists under the ```$PF``` by ensuring ```sriov_numvfs``` is 0

* Create the maximum number of VFs allowed by ```$PF```
```
echo $(cat /sys/class/net/$PF/device/sriov_totalvfs) > /sys/class/net/$PF/device/sriov_numvfs
```

* Checkpoint:
 - Check the number of VFs created under ```$PF``` in ```sriov_numvfs```
 - Check that none of the VFs are created with all zero MAC addresses
 - Assert the number of VF interfaces equals ```sriov_totalvfs```

* Find the maximum MTU allowed by ```$PF```
```
ip -d link list ${PF}
```

* Set the ```$PF``` MTU of the NIC to the max MTU allowed by the ```$PF```, set the MTU of VF 0-{maxVF} to the maximum MTU allowed by the ```$PF```, and set a MAC address
```
While i in {0..$maxVF}; do
    ip link set ${PF} vf $i mac $((basemac + i))
    ip link set ${PF}v$i mtu ${MAX_MTU}
done
```

* Run the clean up

* Repeat the test 100 times

### Clean up
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
ip link set $PF mtu 1500
```
