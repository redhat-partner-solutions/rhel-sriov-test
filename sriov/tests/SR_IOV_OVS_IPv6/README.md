
## Test Case Name: SR-IOV.OVS.IPv6

### Objective(s): Test and ensure IPv6 address on a VF can have the same host suffix as an Open vSwitch virtual port on the same PF (https://bugzilla.redhat.com/show_bug.cgi?id=2138215)  

### Test procedure

* Let "vif_vlan" be the VLAN for the virtual interface, "pf" be the physical interface name that the virtual interface will be created on, and "dut_vif_ipv6" be the IPv6 address that is assigned to the virtual interface. On DUT, Assert on 0 exit code of each of the following steps,
```
systemctl start openvswitch,
ip link del ${pf}.${vif_vlan},
ip link add link ${pf} name ${pf}.${vif_vlan} type vlan id ${vif_vlan},
ip link set ${pf}.${vif_vlan} up,
ovs-vsctl del-br ovs-br0,
ovs-vsctl add-br ovs-br0,
ovs-vsctl add-port ovs-br0 ${pf}.${vif_vlan},
ip -6 addr add ${dut_vif_ipv6}/64 dev ovs-br0,
ip link set ovs-br0 up,
```

* On the trafficgen, create a virual interface with VLAN "vif_vlan" on "trafficgen_pf", and assign an IPv6 address "trafficgen_ipv6" to this virtual interface,
```
ip link add link ${trafficgen_pf} name ${trafficgen_pf}.${vif_vlan} type vlan id ${vif_vlan}
ip -6 addr add ${trafficgen_ipv6}/64 dev ${trafficgen_pf}.${vif_vlan}
ip link set ${trafficgen_pf}.${vif_vlan} up
```

* On the trafficgen, assert ping success to dut_vif_ipv6,
```
ping -W 1 -c 1 {dut_vif_ipv6}
```

* Create 1 VF on the DUT, set this VF's VLAN to "vf_vlan" (a different VLAN than "vif_vlan"), assign an IPv6 address "dut_vf_ipv6" from a different network but with the same host suffix as the "dut_vif_ipv6",
```
echo 0 > /sys/class/net/${pf}/device/sriov_numvfs
echo 1 > /sys/class/net/${pf}/device/sriov_numvfs
ip link set ${pf} vf 0 vlan ${vf_vlan}
ip link set ${pf}v0 up
ip add add ${dut_vf_ipv6}/64 dev ${pf}v0
```

* On trafficgen, delete the existing IPv6 neighbor entry for "dut_vif_ipv6", repeat the same ping test (success last time before the VF is created and assign the IPv6 address). Expect the ping to fail this time, due to (https://bugzilla.redhat.com/show_bug.cgi?id=2138215).
```
ping -W 1 -c 1 {dut_vif_ipv6}
```

### Clean up

* On DUT,
```
ovs-vsctl del-port ovs-br0 ${pf}.${vif_vlan}
ovs-vsctl del-br ovs-br0
ip link del ${pf}.${vif_vlan}
systemctl stop openvswitch
echo 0 > /sys/class/net/${pf}/device/sriov_numvfs
```

* On trafficgen,
```
ip link del ${trafficgen_pf}.${vif_vlan}
```

