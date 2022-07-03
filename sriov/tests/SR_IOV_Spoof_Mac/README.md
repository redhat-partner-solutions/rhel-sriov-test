
## Test Case Name: SR-IOV.Spoof.Mac

### Objective(s): Test and ensure that VF (virtual function) spoof check and custom mac can be set at the same time.

### Test procedure

* On DUT, create 1 VF; set VF 0 spoofchk off and assign a custom mac address; assert on 0 exit code of each of the following steps,
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
echo 1 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
ip link set ${DUT_PF}v0 down
ip link set dev ${DUT_PF} vf 0 spoof off
ip link set ${DUT_PF} vf 0 mac ${DUT_VF0_MAC}
ip link set ${DUT_PF}v0 up
ip add add ${DUT_IP}/24 dev ${DUT_PF}v0
```

* On trafficgen, get its mac address
```
cat /sys/class/net/${TGEN_PF}/address
```

* on DUT, run the following command in a tmux session,
```
timeout 2 nping  --dest-mac ${TGEN_MAC} --source-mac ${SPOOF_MAC} ${TGEN_IP}
```

* On trafficgen use tcpdump to capture packets from the ${SPOOF_MAC}; assert the following exit code == 0
```
timeout 2 tcpdump -i ${trafficgen_PF} -c 1 ether host ${SPOOF_MAC}

```

* Repeat test for spoofchk on; assert the above tcpdump step with exit code != 0

### Clean up
```
echo 0 > /sys/class/net/${DUT_PF}/device/sriov_numvfs
```



