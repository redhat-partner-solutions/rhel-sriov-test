from mock import Mock, patch
from sriov.common.utils import (
    set_vf_mac,
    verify_vf_address,
    get_pci_address,
    bind_driver,
    get_driver,
    config_interface,
    clear_interface,
    add_arp_entry,
    rm_arp_entry,
    prepare_ping_test,
    cleanup_after_ping,
    execute_and_assert,
    set_mtu,
    reset_mtu,
    start_tmux,
    stop_tmux,
    get_intf_mac,
    get_vf_mac,
    vfs_created,
    create_vfs,
    no_zero_macs_pf,
    no_zero_macs_vf,
    set_pipefail,
    execute_until_timeout,
    calc_required_pages_2M,
    get_nic_model,
)  # noqa: E402
import unittest


class UtilsTest(unittest.TestCase):
    def create_mock_ssh_obj(self, code=0, out="", err=""):
        ssh_obj = Mock()
        ssh_obj.name = "mock"
        ssh_obj.execute.return_value = code, out, err
        return ssh_obj

    def create_mock_testdata(self):
        testdata = Mock()
        testdata.ping = {}
        testdata.mtu = {}
        return testdata

    def test_get_pci_address(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["aa:bb:cc:dd:ee:00"], "")
        assert get_pci_address(ssh_obj, "eth0") == "aa:bb:cc:dd:ee:00"

    def test_bind_driver(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert bind_driver(ssh_obj, "0000:00:00.0", "vfio-pci") is True

    def test_get_driver(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["ice"], "")
        assert get_driver(ssh_obj, "ens2f3") == "ice"

    def test_config_interface(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert config_interface(ssh_obj, "eth0", "0", "1.2.3.4") is True

    def test_clear_interface(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert clear_interface(ssh_obj, "eth0", "0") is True

    def test_add_arp_entry(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert add_arp_entry(ssh_obj, "1.2.3.4", "aa:bb:cc:dd:ee:00") is True

    def test_rm_arp_entry(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert rm_arp_entry(ssh_obj, "1.2.3.4") is True

    @patch("sriov.common.utils.clear_interface")
    @patch("sriov.common.utils.config_interface")
    @patch("sriov.common.utils.add_arp_entry")
    def test_prepare_ping_test(
        self, mock_clear_interface, mock_config_interface, mock_add_arp_entry
    ):
        ssh_obj = self.create_mock_ssh_obj()
        mock_clear_interface.return_value = True
        mock_config_interface.return_value = True
        mock_add_arp_entry.return_value = True
        testdata = self.create_mock_testdata()
        assert (
            prepare_ping_test(
                ssh_obj,
                "eth0",
                "0",
                "1.2.3.4",
                "aa:bb:cc:dd:ee:00",
                ssh_obj,
                "1.2.3.4",
                "aa:bb:cc:dd:ee:00",
                testdata,
            )
            is True
        )

    @patch("sriov.common.utils.clear_interface")
    @patch("sriov.common.utils.rm_arp_entry")
    def test_cleanup_after_ping(self, mock_clear_interface, mock_rm_arp_entry):
        ssh_obj = self.create_mock_ssh_obj()
        mock_clear_interface.return_value = True
        mock_rm_arp_entry.return_value = True
        testdata = self.create_mock_testdata()
        assert cleanup_after_ping(ssh_obj, ssh_obj, testdata) is True

    @patch("sriov.common.utils.execute_and_assert")
    def test_set_mtu(self, mock_execute_and_assert):
        ssh_obj = self.create_mock_ssh_obj()
        mock_execute_and_assert.return_value = True
        testdata = self.create_mock_testdata()
        assert set_mtu(ssh_obj, "eth0", ssh_obj, "eth0", 0, 0, testdata) is True

    def test_reset_mtu(self):
        ssh_obj = self.create_mock_ssh_obj()
        testdata = self.create_mock_testdata()
        assert reset_mtu(ssh_obj, ssh_obj, testdata) is True

    def test_start_tmux(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert start_tmux(ssh_obj, "tmux", "cmd") is True

    def test_stop_tmux(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert stop_tmux(ssh_obj, "tmux") is True

    def test_get_intf_mac(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["aa:bb:cc:dd:ee:00"], "")
        assert get_intf_mac(ssh_obj, "eth0") == "aa:bb:cc:dd:ee:00"

    def test_get_vf_mac(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["aa:bb:cc:dd:ee:00"], "")
        assert get_vf_mac(ssh_obj, "eth0", 0) == "aa:bb:cc:dd:ee:00"

    @patch("sriov.common.utils.get_intf_mac")
    def test_set_vf_mac(self, mock_get_intf_mac):
        ssh_obj = self.create_mock_ssh_obj()
        mock_get_intf_mac.return_value = "aa:bb:cc:dd:ee:00"
        assert set_vf_mac(ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:00")
        assert not set_vf_mac(ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:11", timeout=1)

    @patch("sriov.common.utils.get_vf_mac")
    def test_verify_vf_address(self, mock_get_vf_mac):
        mock_get_vf_mac.return_value = "aa:bb:cc:dd:ee:00"
        ssh_obj = self.create_mock_ssh_obj()
        assert verify_vf_address(ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:00")
        assert not verify_vf_address(
            ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:11", timeout=1, interval=0.2
        )

    def test_vfs_created(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["1"], "")
        assert vfs_created(ssh_obj, "eth0", 1) is True

    @patch("sriov.common.utils.vfs_created")
    def test_create_vfs(self, mock_vfs_created):
        ssh_obj = self.create_mock_ssh_obj()
        mock_vfs_created.return_value = True
        assert create_vfs(ssh_obj, "eth0", 1) is True

    def test_no_zero_macs_pf(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["aa:bb:cc:dd:ee:00"], "")
        assert no_zero_macs_pf(ssh_obj, "eth0") is True

        ssh_obj = self.create_mock_ssh_obj(0, ["00:00:00:00:00:00"], "")
        assert no_zero_macs_pf(ssh_obj, "eth0") is False

    def test_no_zero_macs_vf(self):
        ssh_obj = self.create_mock_ssh_obj(0, ["aa:bb:cc:dd:ee:00"], "")
        assert no_zero_macs_vf(ssh_obj, "eth0", 1) is True

        ssh_obj = self.create_mock_ssh_obj(0, ["00:00:00:00:00:00"], "")
        assert no_zero_macs_vf(ssh_obj, "eth0", 1) is False

    def test_set_pipefail(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert set_pipefail(ssh_obj) is True

    def test_execute_and_assert(self):
        ssh_obj = self.create_mock_ssh_obj(0, "output", "errors")
        outs, errs = execute_and_assert(ssh_obj, ["cmd", "cmd_2"], 0)
        assert outs == ["output", "output"]
        assert errs == ["errors", "errors"]

    def test_execute_until_timeout(self):
        ssh_obj = self.create_mock_ssh_obj()
        assert execute_until_timeout(ssh_obj, "cmd") is True

    @patch("sriov.common.utils.get_hugepage_info")
    def test_calc_required_pages_2M(self, mock_get_hugepage_info):
        ssh_obj = self.create_mock_ssh_obj()

        testcases = [
            {"2M": (0, 0), "1G": (0, 0), "instance": 1, "expected": 200},
            {"2M": (0, 0), "1G": (1, 1), "instance": 1, "expected": 0},
            {"2M": (0, 0), "1G": (1, 0), "instance": 1, "expected": 200},
            {"2M": (200, 200), "1G": (1, 0), "instance": 1, "expected": 0},
            {"2M": (200, 199), "1G": (1, 0), "instance": 1, "expected": 201},
            {"2M": (200, 199), "1G": (1, 1), "instance": 1, "expected": 0},
            {"2M": (200, 199), "1G": (1, 0), "instance": 2, "expected": 401},
        ]

        for testcase in testcases:

            def get_hugepage_info_side_effect(*args, **kwargs):
                if args[1] == "2M":
                    return testcase["2M"]
                elif args[1] == "1G":
                    return testcase["1G"]
                else:
                    raise Exception("Invalid input")

            mock_get_hugepage_info.side_effect = get_hugepage_info_side_effect
            actual = calc_required_pages_2M(ssh_obj, testcase["instance"])
            expected = testcase["expected"]
            assert actual == expected, f"actual: {actual}, expected: {expected}"

    def test_get_nic_model(self):
        ssh_obj = self.create_mock_ssh_obj(
            0,
            [
                "             CPUID     PCI (sysfs)           ISA PnP       PnP "
                + "(sysfs)           PCMCIA      PCMCIA      Virtual I/O (VIRTIO) "
                + "devices                            IBM Virtual I/O (VIO)       "
                + "              kernel device tree (sysfs)                       "
                + "   USB   IDE   SCSI    NVMe    MMC   sound     graphics        "
                + "input     S/390 devices             Network interfaces         "
                + "         Framebuffer devices                   Display       "
                + "CPUFreq       ABI   pci@0000:00:00.0  ens0f0      network      "
                + "  Ethernet Controller XXV710 for 25GbE SFP28\n"
            ],
            "",
        )
        assert (
            get_nic_model(ssh_obj, "ens0f0")
            == "Ethernet Controller XXV710 for 25GbE SFP28"
        )


if __name__ == "__main__":
    unittest.main()
