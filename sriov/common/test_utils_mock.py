from mock import Mock, patch
import os
from sriov.common.utils import set_vf_mac, verify_vf_address  # noqa: E402
import sys
import unittest


class UtilsTest(unittest.TestCase):
    @patch("sriov.common.utils.get_intf_mac")
    def test_set_vf_mac(self, mock_get_intf_mac):
        ssh_obj = Mock()
        ssh_obj.execute.return_value = 0, "", ""
        mock_get_intf_mac.return_value = "aa:bb:cc:dd:ee:00"
        assert set_vf_mac(ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:00")
        assert not set_vf_mac(ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:11", timeout=1)

    @patch("sriov.common.utils.get_vf_mac")
    def test_verify_vf_address(self, mock_get_vf_mac):
        mock_get_vf_mac.return_value = "aa:bb:cc:dd:ee:00"
        ssh_obj = Mock()
        assert verify_vf_address(ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:00")
        assert not verify_vf_address(
            ssh_obj, "eth0", 0, "aa:bb:cc:dd:ee:11", timeout=1, interval=0.2
        )


if __name__ == "__main__":
    unittest.main()
