
## Test Case Name: SR-IOV.macAddress.IPv6

### Objective(s): Test and ensure that VF (virtual function) admin MAC address functions as intended with IPv6.

### Test procedure

* On trafficgen, clean up existing IPv6 address and neighbor discovery(ND) cache, and add an IPv6 address,
```
ip -6 add del ${TGEN_IPv6}/64 dev ${TGEN_PF}
ip -6 neigh del ${DUT_IPv6} dev ${TGEN_PF}
ip -6 add add ${TGEN_IPv6}/64 dev ${TGEN_PF}
```

* On DUT, clean up existing IPv6 ND cache, and create 1 VF and assign a mac address. Assert on 0 exit code of each of the following steps,
```
ip -6 neigh del {TGEN_IPv6} dev ${DUT_PF}
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF}v0 down
ip link set ${DUT_PF} vf 0 mac ${DUT_VF0_MAC}
ip link set ${DU_PF}v0 up
ip -6 add add ${DUT_IPv6}/64 dev ${DUT_PF}v0
```

* On trafficgen: assert on ping exit code 0
```
ping -6 -W 1 -c 1 ${DUT_IPv6}
```

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
