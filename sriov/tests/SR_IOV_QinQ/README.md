
## Test Case Name: SR-IOV.QinQ

### Objective(s): Test and ensure that QinQ on VF works with kernel drive.

### Test procedure

* Create 1 VF on PF 1; assign an outside vlan to the VF; create sub-interface with an inside vlan; assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${PF} vf 0 vlan ${OUTSIDE_VLAN} proto 802.1ad
ip link add link ${PF}v0 name ${PF}v0.${INSIDE_VLAN} type vlan id ${INSIDE_VLAN}
ip add add ${DUT_IP}/24 dev ${PF}v0.${INSIDE_VLAN}
```

* Use the VF 0 sub-interface to send packets to the trafficgen,
```
timeout 3 nping --dest-mac {trafficgen_mac} {trafficgen_ip}
```

* On the trafficgen, use tcpdump to sniff the inbound QinQ packets and assert tcpdump receive the QinQ packets,
```
timeout 3 tcpdump -i ${trafficgen_pf} -c 1 vlan ${OUTSIDE_VLAN} and vlan ${INSIDE_VLAN}
```

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```



