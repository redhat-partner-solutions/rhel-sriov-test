## Test Case Name: SR-IOV.BondVF
# UUID: a1df2b99-97af-4290-b55a-2aa777ced821

### Objective(s): Test and ensure that VFs kernel bond across PFs works as expected.

### Test procedure

* This test case will iterate over bond mode and whether or not using explicit bond mac

* On DUT, create 1 VF on PF 1 and 1 VF on PF 2; set trust mode on; and set the created virtual interface down,
```
echo 1 > /sys/class/net/${PF_1}/device/sriov_numvfs
echo 1 > /sys/class/net/${PF_2}/device/sriov_numvfs
ip link set ${PF_1} vf 0 trust on
ip link set ${PF_2} vf 0 trust on
ip link set ${PF_1}v0 down
ip link set ${PF_2}v0 down
```

* On DUT, form a bond interface across the 2 VFs with the following permutations,

| MODE (0/1) | explicit_mac (True/False) |
| ---------- | ----- |

```
modprobe bonding
echo +bond0 > /sys/class/net/bonding_masters
ip link set bond0 down
ip link set bond0 address ${BOND_MAC} # only if explicit_mac is true
echo ${MODE} > /sys/class/net/bond0/bonding/mode
echo 100 > /sys/class/net/bond0/bonding/miimon
echo +${PF_1}v0 > /sys/class/net/bond0/bonding/slaves
echo +${PF_2}v0 > /sys/class/net/bond0/bonding/slaves
echo ${PF_1}v0 > /sys/class/net/bond0/bonding/primary
ip link set bond0 up
```

* On DUT, prepare for ping test,
```
ip address add ${BOND_IP}/24 dev bond0
arp -s ${PING_IP} ${PING_MAC}
```

* On DUT start a tmux session, in the tmux session continuously send ping packets to ${PING_IP}

* On trafficgen, use tcpdump to validate the ping packets are received on the primary link

* This step is for mode 1 only, on DUT, disable PF_1_VF_0,
```
ip link set ${PF_1} vf 0 state disable
```

* On trafficgen, use tcpdump to validate the ping packets are received on the TGEN_PF_2

* This step is for mode 1 only. On DUT, enable VF 0; On trafficgen, use tcpdump to validate the ping packets are received on the TGEN_PF_1


### Clean up

* On trafficgen, delete the ping tmux session

* On DUT, in the testpmd tmux window, enter “quit\n”, then delete testpmd tmux session, and reset the VFs
