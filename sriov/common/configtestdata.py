from sriov.common.config import Config


class ConfigTestData:
    def __init__(self, settings: Config) -> None:
        """Init the testdata object

        Args:
            self:
            settings (Config): config object
        """
        self.vlan = 10
        if "vlan" in settings.config:
            self.vlan = int(settings.config["vlan"])
        self.dut_ip = "101.1.1.2"
        self.dut_ip_v6 = "2001::2"
        self.dut_mac = "aa:bb:cc:dd:ee:00"
        self.dut_spoof_mac = "aa:bb:cc:dd:ee:ff"
        self.trafficgen_ip = "101.1.1.1"
        self.trafficgen_ip_v6 = "2001::1"
        self.trafficgen_spoof_mac = "aa:00:00:00:00:00"
        self.qos = 5
        self.max_tx_rate = 10
        self.pfs = {}
        self.vfs = {}
        self.pf_net_paths = {}
        # NOTE: These should be done in a loop going forward
        for interface in settings.config["dut"]["interface"]:
            if "pf" in interface:
                self.pfs[interface] = settings.config["dut"]["interface"][interface]
                self.pf_net_paths[interface] = (
                    "/sys/class/net/"
                    + settings.config["dut"]["interface"][interface]["name"]
                    + "/device"
                )
            else:
                self.vfs[interface] = settings.config["dut"]["interface"][interface]
        self.tmux_session_name = "sriov_job"
        self.ping = {}  # track ping test
        self.mtu = {}  # track mtu change
