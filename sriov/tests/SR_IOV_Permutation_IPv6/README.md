
## Test Case Name: SR-IOV.Permutation.IPv6

### Objective(s): IPv6 ping test for VFs (virtual function) configuration with different properties combined

### Test procedure

* On DUT, create 1 VF; set VF 0 with a permutation of the following permutations,

| Spoofchk (on/off) | Trust(on/off) | vlan(with/without) | QoS (with/without) | max_tx_rate (with/without) |
| --- | --- | --- | --- | --- |

assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/{DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/{DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF}v0 down
ip link set ${DUT_PF} vf 0 mac ${DUT_VF0_MAC}
ip link set ${DUT_PF} vf 0 spoof ${spoof}
ip link set ${DUT_PF} vf 0 trust ${trust}
# next line only if vlan is set
ip link set ${DUT_PF} vf 0 vlan ${vlan} qos ${qos}
# next line only if max_tx_rate is set
ip link set ${DUT_PF} vf 0 max_tx_rate ${max_tx_rate}
ip -6 address add ${DUT_IPv6}/64 dev ${DUT_PF}v0
ip link set ${DUT_IP}v0 up
```

* On trafficgen,
```
ip -6 address add ${TGEN_IPv6}/64 dev ${TGEN_PF}
```

* On trafficgen: assert on ping exit code 0
```
ping -6 -W 1 -c 1 ${DUT_IPv6}
```

* Repeat test with next permutation

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```
