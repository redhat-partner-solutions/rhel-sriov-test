## Test Case Name: SR-IOV.BondVF.DPDK

### Objective(s): Test and ensure that VFs DPDK bond across PFs works as expected.

### Test procedure

* This test case will iterate over bond mode and whether or not using explicit bond mac

* On DUT, create 2 VF on PF 1 and 1 VF on PF 2; set trust mode on; and set a specific mac address under PF1 VF 1,
```
echo 2 > /sys/class/net/${PF_1}/device/sriov_numvfs
echo 1 > /sys/class/net/${PF_2}/device/sriov_numvfs
ip link set ${PF_1} vf 0 trust on
ip link set ${PF_1} vf 1 trust on
ip link set ${PF_2} vf 0 trust on
ip link set ${PF_1} VF 1 mac ${PF_1_VF_1_MAC}
```

* On DUT, get the PCI address for each VF. Compare the PCI address PF_1 VF 1 and PF_2 VF 0, if PF_1 VF 1 has a smaller PCI address, set IN_NUM=1; else set IN_NUM=2

* On DUT, bind all VFs to vfio-pci

* On DUT, start a tmux session and run testpmd in the tmux session, for example,

| MODE (0/1) | explicit_mac (True/False) |
| ---------- | ----- |

```
podman run -it --rm --privileged -v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules --cpuset-cpus 30,32,34 docker.io/patrickkutch/dpdk:v21.11 dpdk-testpmd -l 30,32,34 -n 4 -a ${PF_1_VF_0_PCI} -a ${PF_1_VF_1_PCI} -a ${PF_2_VF_0_PCI} --vdev net_bonding_bond_test,mode=${MODE},slave=${PF_1_VF_0_PCI},slave=${PF_2_VF_0_PCI},primary=${PF_1_VF_0_PCI}<",mac=${BOND_MAC}" if explicit_mac> -- --forward-mode=mac --stats-period=1 --portlist ${IN_NUM},3 --eth-peer 3,dd:cc:bb:aa:33:00
```

* On trafficgen, prepare for ping test,
```
ip address add ${PING_IP}/24 dev ${TGEN_PF_1}
arp -s ${PING_IP} {PF_1_VF_1_MAC}
```

* On trafficgen, start a tmux session to continuously send ping packets to ${PING_IP}

* On trafficgen, use tcpdump to validate the ping packets are received on the TGEN_PF_1

* This step is for mode 1 only, on DUT, disable PF_1_VF_0,
```
ip link set ${PF_1} vf 0 state disable
```

* On trafficgen, use tcpdump to validate the ping packets are received on the TGEN_PF_2

* This step is for mode 1 only. On DUT, enable VF 0; On trafficgen, use tcpdump to validate the ping packets are received on the TGEN_PF_1


### Clean up

* On trafficgen, delete the ping tmux session

* On DUT, in the testpmd tmux window, enter “quit\n”, then delete testpmd tmux session, and reset the VFs
