
## Test Case Name: SR-IOV.MTU

### Objective(s): Test and ensure that VF (virtual function) MTU functions as intended.

### Test procedure

* On DUT, find the maxmtu using `ip -d link list`; do the same on the trafficgen; use the minimum of these two as the common MTU size. In case a switch sits between the DUT and the trafficgen, a switch MTU can be specified, the minimum of the three will be used as the common MTU size.

* On DUT, create 1 VF with the common MTU; assert 0 exit code on each of the following steps,
```
echo 0 > /sys/class/net/$PF/device/sriov_numvfs
echo 1 > /sys/class/net/$PF/device/sriov_numvfs
ip link set ${PF} mtu ${MTU}
ip link set ${PF}v0 mtu ${MTU}
ip link set ${PF}v0 up
ip add add ${DUT_IP}/24 dev ${PF}v0
arp -s ${TGEN_IP} ${TGEN_MAC}
```

* On trafficgen,
```
ip link set ${TGEN_PF} mtu ${MTU}
ip addr add ${TGEN_IP}/24 dev ${TGEN_PF}
arp -s ${DUT_IP} ${DUT_VF0_MAC}
```

* On DUT, ping trafficgen with MTU size, and assert ping success,
```
ping -W 1 -c -s $((MTU-28)) -M do ${TGEN_IP}
```

* Delete ip address and the arp entry from the DUT and the trafficgen; set MTU size back to 1500

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
