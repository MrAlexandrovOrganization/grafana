import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


class DashboardInstallTests(unittest.TestCase):
    def test_private_deploy_umask_keeps_dashboards_readable_by_grafana(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "monitoring"
            dashboard = destination / "grafana-dashboards/vpn-traffic.json"
            for existing in (False, True):
                if existing:
                    dashboard.chmod(0o600)
                    dashboard.parent.chmod(0o700)
                subprocess.run(
                    ["make", "directories", f"MONITORING_DATA_DIR={destination}"],
                    cwd=root,
                    preexec_fn=lambda: os.umask(0o077),
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(stat.S_IMODE(dashboard.stat().st_mode), 0o644)
                self.assertEqual(stat.S_IMODE(dashboard.parent.stat().st_mode), 0o755)
                self.assertEqual(json.loads(dashboard.read_text())["uid"], "vpn-traffic")


if __name__ == "__main__":
    unittest.main()
