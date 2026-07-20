from __future__ import annotations

import contextlib
import io
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run


class RunnerTests(unittest.TestCase):
    def test_version_major_parser(self) -> None:
        self.assertEqual(run._major("v22.4.1"), 22)
        self.assertEqual(run._major("unavailable"), 0)

    def test_cli_modes_are_mutually_exclusive(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run.parse_args(["--dev", "--doctor"])

    def test_frontend_build_detects_missing_and_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            frontend = Path(raw)
            (frontend / "src").mkdir()
            (frontend / "public").mkdir()
            with patch.object(run, "FRONTEND", frontend):
                self.assertTrue(run.frontend_needs_build())
                dist = frontend / "dist"
                dist.mkdir()
                index = dist / "index.html"
                index.write_text("built", encoding="utf-8")
                os.utime(index, (2000, 2000))
                self.assertFalse(run.frontend_needs_build())
                source = frontend / "src" / "App.tsx"
                source.write_text("changed", encoding="utf-8")
                os.utime(source, (3000, 3000))
                self.assertTrue(run.frontend_needs_build())

    def test_port_check_reports_bound_port(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            self.assertFalse(run.port_available("127.0.0.1", port))


if __name__ == "__main__":
    unittest.main()
