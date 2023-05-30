
## Test Case Name: SR-IOV.InterVF.Multicast.IPv6

### Objective(s): Test and ensure that VFs (virtual function) on the same PF can receive IPv6 multicast neighbor discovery from trafficgen

### Test procedure

* Let "vlan" be the VLAN for the virtual interfaces, "PF" be the physical interface name on DUT that the virtual interface will be created on, "DUT_IPv6_0" and "DUT_IPv6_1" be the IPv6 addresses that are assigned to DUT virtual interfaces.

* On DUT, Create two namespaces and two VF,
```
ip netns add ns0
ip netns add ns1
echo 0 > /sys/class/net/{PF}/device/sriov_numvfs
echo 2 > /sys/class/net/{PF}/device/sriov_numvfs
```

* Use the following vf settings: trust on, spoof off, vlan on. Assign the VFs to the namespaces, one for each; assign IPv6 addresses from the same subnet and bring both VFs up. Assert on 0 exit code of each of the following steps,
```
ip link set ${PF} vf 0 spoof off
ip link set ${PF} vf 0 trust on
ip link set ${PF} vf 0 vlan ${vlan}
ip link set ${PF}v0 netns ns0
ip netns exec ns0 ip link set ${PF}v0 up
ip netns exec ns0 ip -6 address add ${DUT_IPv6_0}/64 dev ${PF}v0

ip link set ${PF} vf 1 spoof off
ip link set ${PF} vf 1 trust on
ip link set ${PF} vf 1 vlan ${vlan}
ip link set ${PF}v1 netns ns1
ip netns exec ns1 ip link set ${PF}v1 up
ip netns exec ns1 ip -6 address add ${DUT_IPv6_1}/64 dev ${PF}v1
```

* On the trafficgen, create a virual interface with VLAN "vlan" on "trafficgen_pf", and assign an IPv6 address from the same subnet "trafficgen_ipv6" to to this virtual interface,
```
ip link add link ${trafficgen_pf} name ${trafficgen_pf}.${vlan} type vlan id ${vlan}
ip -6 addr add ${trafficgen_ipv6}/64 dev ${trafficgen_pf}.${vlan}
ip link set ${trafficgen_pf}.${vlan} up
```

* Wait 3 seconds for IPv6 neighbor established

* On the trafficgen, assert ping success to DUT_IPv6_0 and DUT_IPv6_1,
```
ping -W 1 -c 1 {DUT_IPv6_0}
ping -W 1 -c 1 {DUT_IPv6_1}
```
That confirms IPv6 multicast neighbor discovery success for every DUT address.


### Clean up

* On DUT,
```
ip netns del ns0
ip netns del ns1
echo 0 > /sys/class/net/${PF}/device/sriov_numvfs
```

* On trafficgen,
```
ip link del ${trafficgen_pf}.${vlan}
```

