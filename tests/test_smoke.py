import importlib.util
import io
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    "smoke", Path(__file__).resolve().parents[1] / "scripts/smoke.py"
)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class Response(io.BytesIO):
    status = 200


class SustainedReadinessTests(unittest.TestCase):
    def test_startup_failure_resets_success_window(self):
        states = iter([True, True, False, True, True, True])
        waits = []

        def request(*args, **kwargs):
            if not next(states):
                raise OSError("synthetic startup restart")
            return Response(b'{"database":"ok"}')

        smoke.verify("grafana", attempts=6, request=request, sleep=waits.append)
        self.assertEqual(len(waits), 5)

    def test_brief_health_response_does_not_confirm_deployment(self):
        with self.assertRaises(SystemExit):
            smoke.verify(
                "grafana",
                attempts=2,
                request=lambda *args, **kwargs: Response(b'{"database":"ok"}'),
                sleep=lambda _: None,
            )
