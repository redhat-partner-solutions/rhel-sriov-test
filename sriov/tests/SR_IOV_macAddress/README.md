
## Test Case Name: SR-IOV.macAddress

### Objective(s): Test and ensure that VF (virtual function) MAC address functions as intended.

### Test procedure

* On DUT, create 1 VF and assign a mac address. Assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF}v0 down
ip link set ${DUT_PF} vf 0 mac ${DUT_VF0_MAC}
ip link set ${DU_PF}v0 up
ip add add ${DUT_IP}/24 dev ${DUT_PF}v0
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

* On trafficgen, remove arp entry and ip address,
```
arp -d ${DUT_IP}
ip addr del ${TGEN_IP}/24 dev ${TGEN_PF}
```

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```



