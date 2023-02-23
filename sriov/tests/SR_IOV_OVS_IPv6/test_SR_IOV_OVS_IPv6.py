import pytest
from sriov.common.utils import (
    create_vfs,
    execute_and_assert,
    execute_until_timeout,
    delete_ipv6_neighbor,
    prepare_ping_ipv6_test,
    is_package_installed,
)


dut_vif_ipv6 = "2001:1b74:4d9:1002::4"
trafficgen_ipv6 = "2001:1b74:4d9:1002::5"
# VF ip has different network portion as the VIF, but same host portion
dut_vf_ipv6 = "2001:1b74:4d9:1003::4"


@pytest.fixture
def ovs_setup(dut, trafficgen, settings, testdata):
    if not is_package_installed(dut, "openvswitch"):
        pytest.skip("OVS package not installed")

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    vif_vlan = testdata.vlan

    delete_ipv6_neighbor(dut, trafficgen_ipv6)
    delete_ipv6_neighbor(trafficgen, dut_vif_ipv6)

    du_steps = [
        "systemctl start openvswitch",
        f"ip link del {pf}.{vif_vlan} || true",
        f"ip link add link {pf} name {pf}.{vif_vlan} type vlan id {vif_vlan}",
        f"ip link set {pf}.{vif_vlan} up",
        "ovs-vsctl del-br ovs-br0 || true",
        "ovs-vsctl add-br ovs-br0 || true",
        f"ovs-vsctl add-port ovs-br0 {pf}.{vif_vlan}",
        f"ip -6 addr add {dut_vif_ipv6}/64 dev ovs-br0",
        "ip link set ovs-br0 up",
    ]
    execute_and_assert(dut, du_steps, 0, 0.1)

    yield

    du_cleanups = [
        f"ovs-vsctl del-port ovs-br0 {pf}.{vif_vlan}",
        "ovs-vsctl del-br ovs-br0",
        f"ip link del {pf}.{vif_vlan}",
        "systemctl stop openvswitch",
    ]
    execute_and_assert(dut, du_cleanups, 0, 0.1)


@pytest.mark.xfail(reason="https://bugzilla.redhat.com/show_bug.cgi?id=2138215")
def test_SR_IOV_OVS_IPv6(
    dut, trafficgen, settings, testdata, ovs_setup
):
    """Test IPv6 on a VF sharing the same PF with a openvswitch virtual port

    Args:
        dut:         ssh connection obj
        trafficgen:  trafficgen obj
        settings:    settings obj
        testdata:    testdata obj
    """
    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]

    prepare_ping_ipv6_test(trafficgen, trafficgen_pf, testdata.vlan,
                           trafficgen_ipv6, dut_vif_ipv6, testdata)

    assert execute_until_timeout(trafficgen, f"ping -W 1 -c 1 {dut_vif_ipv6}")

    create_vfs(dut, pf, 1)

    # VF vlan is not important
    vf_vlan = testdata.vlan + 1
    steps = [
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 vlan {vf_vlan}",
        f"ip -6 addr add {dut_vf_ipv6}/64 dev {pf}v0",
        f"ip link set {pf}v0 up",
    ]
    execute_and_assert(dut, steps, 0, 0.1)
    delete_ipv6_neighbor(trafficgen, dut_vif_ipv6)
    assert execute_until_timeout(trafficgen, f"ping -W 1 -c 1 {dut_vif_ipv6}")
