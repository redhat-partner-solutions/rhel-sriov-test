
## Test Case Name: SR-IOV.TrustMode

### Objective(s): Test and ensure that VF (virtual function) trust mode functions as intended.

### Test procedure

* On DUT, create 1 VF; set VF 0 trust mode to on; assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF}v0 down
ip link set ${DUT_PF} vf 0 mac ${MAC_1}
ip link set ${DUT_PF} vf 0 trust on
ip link set ${DUT_PF}v0 address ${MAC_2}
ip link set ${DUT_PF}v0 up
```

* Read VF 0 mac address and assert it is equal to ${MAC_2}

* On DUT, assert on 0 exit code of the following step,

```
ip link set ${DUT_PF} vf 0 trust off
```

* The next step is expected to produce an error,
  
```
ip link set ${DUT_PF}v0 address ${MAC_3}
RTNETLINK answers: Permission denied
```

* Read VF 0 mac address and assert it is not equal to ${MAC_3}

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```



