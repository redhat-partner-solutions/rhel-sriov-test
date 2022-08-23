import pytest
from sriov.common.utils import create_vfs, execute_and_assert, start_tmux, stop_tmux


@pytest.mark.parametrize("spoof", ("on", "off"))
def test_SR_IOV_Spoof_Mac(dut, trafficgen, settings, testdata, spoof):
    """Test and ensure that VF spoof check and custom mac can be set at the same time

    Args:
        dut:        ssh connection obj
        trafficgen: trafficgen object
        settings:   settings obj
        testdata:   testdata obj
        spoof:      spoof parameter
    """

    pf = settings.config["dut"]["interface"]["pf1"]["name"]
    steps = [
        f"ip link set {pf}v0 down",
        f"ip link set {pf} vf 0 mac {testdata.dut_mac}",
        f"ip link set {pf} vf 0 spoof {spoof}",
        f"ip add add {testdata.dut_ip}/24 dev {pf}v0",
        f"ip link set {pf}v0 up",
    ]

    create_vfs(dut, pf, 1)

    execute_and_assert(dut, steps, 0, 0.1)

    trafficgen_pf = settings.config["trafficgen"]["interface"]["pf1"]["name"]
    trafficgen_mac = settings.config["trafficgen"]["interface"]["pf1"]["mac"]
    spoof_mac = testdata.dut_spoof_mac
    trafficgen_ip = testdata.trafficgen_ip  # noqa: F841
    tmux_session = testdata.tmux_session_name
    tmux_cmd = f"timeout 3 nping --dest-mac {trafficgen_mac} --source-mac \
               {spoof_mac} {trafficgen_ip}"
    print(tmux_cmd)
    assert start_tmux(dut, tmux_session, tmux_cmd)
    tgen_cmd = f"timeout 3 tcpdump -i {trafficgen_pf} -c 1 ether host {spoof_mac}"
    trafficgen.log_str(tgen_cmd)
    code, out, err = trafficgen.execute(tgen_cmd)
    assert stop_tmux(dut, tmux_session)
    if spoof == "off":
        assert code == 0, err
    else:
        assert code != 0, err
