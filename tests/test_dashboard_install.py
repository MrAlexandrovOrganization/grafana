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
            dashboards = destination / "grafana-dashboards"
            dashboards.mkdir(parents=True)
            unrelated = dashboards / "another-project.json"
            unrelated.write_text('{"uid":"another-project"}\n')
            for existing in (False, True):
                if existing:
                    for source in (root / "dashboards").glob("*.json"):
                        (dashboards / source.name).chmod(0o600)
                    dashboards.chmod(0o700)
                subprocess.run(
                    ["make", "directories", f"MONITORING_DATA_DIR={destination}"],
                    cwd=root,
                    preexec_fn=lambda: os.umask(0o077),
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(stat.S_IMODE(dashboards.stat().st_mode), 0o755)
                for source in (root / "dashboards").glob("*.json"):
                    installed = dashboards / source.name
                    self.assertEqual(stat.S_IMODE(installed.stat().st_mode), 0o644)
                    self.assertEqual(json.loads(installed.read_text()), json.loads(source.read_text()))
                self.assertEqual(unrelated.read_text(), '{"uid":"another-project"}\n')


if __name__ == "__main__":
    unittest.main()
