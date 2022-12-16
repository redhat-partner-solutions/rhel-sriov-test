
## Test Case Name: SR-IOV.macAddressDuplicate

### Objective(s): Test and ensure that duplicate mac address across VFs on the same PF is permitted.

### Test procedure

* On DUT, create 2 VFs; set VF 0 mac address to ${MAC_1}; set VF 0 mac address to ${MAC_2}; assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 2 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF} vf 0 mac ${MAC_1}
ip link set ${DUT_PF} vf 0 mac ${MAC_2}
```

* Read VF 0 mac address and assert it is equal to ${MAC_1}

* Read VF 1 mac address and assert it is equal to ${MAC_2}


* Swap mac addresses between VFs. On DUT, assert on 0 exit code of the following steps,

```
ip link set ${DUT_PF} vf 0 mac ${MAC_2}
ip link set ${DUT_PF} vf 0 mac ${MAC_1}
```

* Read VF 0 mac address and assert it is equal to ${MAC_2}

* Read VF 1 mac address and assert it is equal to ${MAC_1}

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
