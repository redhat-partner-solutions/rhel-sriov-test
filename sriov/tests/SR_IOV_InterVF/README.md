
## Test Case Name: SR-IOV.InterVF
# 5d23e6c6-7954-48de-ab5a-d8da6b7b45c5

### Objective(s): Test and ensure that VFs (virtual function) on the same PF can communicate

### Test procedure

* On DUT, Create two namespaces and two VF,
```
ip netns add ns0
ip netns add ns1
echo 0 > /sys/class/net/{pf}/device/sriov_numvfs
echo 2 > /sys/class/net/{pf}/device/sriov_numvfs
```

* On DUT, set up the VF with a permutation; assert on 0 exit code of each permutation setup

| Spoofchk (on/off) | Trust(on/off) | vlan(with/without) | QoS (with/without) | max_tx_rate (with/without) |
| --- | --- | --- | --- | --- |

* Assign the VFs to the namespaces, one for each; assert on 0 exit code of each of the following steps,
```
ip link set ${PF}v0 netns ns0
ip link set ${PF}v1 netns ns1
ip netns exec ns0 ip link set ${PF}v0 up
ip netns exec ns0 ip add add ${DUT_IP_0}/24 dev ${PF}v0
ip netns exec ns1 ip link set ${PF}v1 up
ip netns exec ns1 ip add add ${DUT_IP_1}/24 dev ${PF}v1
```

* In each namespace, set up an arp entry for the ip address in the other name space,
```
ip netns exec ns0 arp -s ${DUT_IP_1} ${DUT_VF1_MAC}
ip netns exec ns1 arp -s ${DUT_IP_0} ${DUT_VF0_MAC}
```

* From the ns0 ping ns1 address. Assert exit code of ping equal to 0,
```
ip netns exec ns0 ping ${DUT_IP_1}/24
```

* Delete the namespaces

* Repeat test with next permutation

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
