
## Test Case Name: SR-IOV.InterVF.IPv6

### Objective(s): Test and ensure that VFs (virtual function) on the same PF can communicate via IPv6

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
ip netns exec ns0 ip -6 address add ${DUT_IPv6_0}/24 dev ${PF}v0
ip netns exec ns1 ip link set ${PF}v1 up
ip netns exec ns1 ip -6 address add ${DUT_IPv6_1}/24 dev ${PF}v1
```

* Wait 3 seconds for IPv6 neighbor established

* From the ns0 ping ns1 address. Assert exit code of ping equal to 0,
```
ip netns exec ns0 ping -6 ${DUT_IPv6_1}/24
```

* Delete the namespaces

* Repeat test with next permutation

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
