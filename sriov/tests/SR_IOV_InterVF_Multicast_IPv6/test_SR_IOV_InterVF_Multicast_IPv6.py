from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    execute_until_timeout,
    prepare_ping_ipv6_test,
)

ipv6_prefix = "2001:1b74:4d9:1002::"
trafficgen_ipv6 = f"{ipv6_prefix}5"


def test_SR_IOV_InterVF_Multicast_IPv6(
    dut,
    trafficgen,
    settings,
    testdata,
):
    """Test and ensure that VFs on the same PF can receive IPv6 multicast neighbor
       discovery from trafficgen

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]

    steps = []
    for i in range(2):
        steps.extend(
            [
                f"ip netns add ns{i}",
                f"ip link set {pf} vf {i} spoof off",
                f"ip link set {pf} vf {i} trust on",
                f"ip link set {pf} vf {i} vlan {testdata.vlan}",
            ]
        )
        steps.append(f"ip link set {pf}v{i} netns ns{i}")
        steps.append(
            f"ip netns exec ns{i} ip -6 addr add {ipv6_prefix}{i+1}/64 dev {pf}v{i}"
        )
        steps.append(f"ip netns exec ns{i} ip link set {pf}v{i} up")

    assert create_vfs(dut, pf, 2)
    execute_and_assert(dut, steps, 0, 0.1)

    prepare_ping_ipv6_test(
        trafficgen, trafficgen_pf, testdata.vlan, trafficgen_ipv6, None, testdata
    )

    assert execute_until_timeout(trafficgen, f"ping -W 1 -c 1 {ipv6_prefix}1")
    assert execute_until_timeout(trafficgen, f"ping -W 1 -c 1 {ipv6_prefix}2")

    # cleanup
    steps = [
        "ip netns del ns0",
        "ip netns del ns1",
    ]
    execute_and_assert(dut, steps, 0)
