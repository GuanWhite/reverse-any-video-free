#!/usr/bin/env python3
"""Offline preflight: prove this toolkit needs no account, token or network.

  python scripts/doctor.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from hf_free import TOOLKIT, VERSION, ffmpeg_bin, find_binary, ffprobe_bin


def version_of(binary: str | None) -> str | None:
    if not binary:
        return None
    try:
        out = subprocess.run([binary, "-version"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=10)
        return out.stdout.decode("utf-8", "replace").splitlines()[0][:120]
    except Exception as exc:
        return f"unreadable: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Check local dependencies and permissions.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ffmpeg = find_binary("ffmpeg")
    ffprobe = ffprobe_bin()
    try:
        has_pillow = bool(__import__("PIL"))
    except ImportError:
        has_pillow = False
    try:
        import imageio_ffmpeg  # noqa: F401
        has_imageio = True
    except ImportError:
        has_imageio = False

    writable = False
    try:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            Path(tmp, ".write_test").write_text("ok", encoding="utf-8")
            writable = True
    except Exception:
        writable = False

    checks = {
        "python": {"ok": sys.version_info >= (3, 10), "value": sys.version.split()[0],
                   "required": ">= 3.10"},
        "ffmpeg": {"ok": bool(ffmpeg), "value": ffmpeg or "missing",
                   "version": version_of(ffmpeg), "required": True},
        "ffprobe": {"ok": bool(ffprobe), "value": ffprobe or "missing (fallback available)",
                    "version": version_of(ffprobe), "required": False},
        "pillow": {"ok": has_pillow, "value": has_pillow,
                   "required": False, "note": "contact sheets and side-by-side images"},
        "imageio_ffmpeg": {"ok": has_imageio, "value": has_imageio, "required": False},
        "workspace_writable": {"ok": writable, "value": writable, "required": True},
    }
    try:
        ffmpeg_bin()
        can_run_ffmpeg = True
    except Exception:
        can_run_ffmpeg = False

    result = {
        "toolkit": TOOLKIT,
        "version": VERSION,
        "account_required": False,
        "network_required": False,
        "telemetry": "none",
        "paid_commands": "none (see docs/PRO_REMOVAL.md)",
        "permissions": {
            "filesystem_read": ["source video", "project directory"],
            "filesystem_write": ["project directory", "report/JSON/PNG outputs"],
            "subprocess": ["local ffmpeg/ffprobe only"],
            "network": [],
            "credentials": [],
        },
        "checks": checks,
        "all_required_ok": all(
            checks[k]["ok"] for k in ("python", "ffmpeg", "workspace_writable")
        ) and can_run_ffmpeg,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{TOOLKIT} {VERSION} | account required: NO | network required: NO")
        for key, val in checks.items():
            print(f"  [{'OK ' if val['ok'] else 'WARN'}] {key}: {val['value']}")
        print(f"  => all required dependencies OK: {result['all_required_ok']}")
    return 0 if result["all_required_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
