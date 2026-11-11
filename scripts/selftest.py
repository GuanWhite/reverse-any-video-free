#!/usr/bin/env python3
"""End-to-end offline self-test. No downloads, no account, no network.

Generates a synthetic 6 s / 30 fps clip with two hard cuts (frames 60 and 120)
and a sine tone, then runs doctor -> probe -> cuts -> frames -> diff and asserts
the toolkit reproduces the known ground truth.

  python scripts/selftest.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hf_free import ffmpeg_bin

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def make_clip(path: Path) -> None:
    cmd = [
        ffmpeg_bin(), "-v", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=2",
        "-f", "lavfi", "-i", "color=c=navy:size=320x180:rate=30:duration=2",
        "-f", "lavfi", "-i", "smptebars=size=320x180:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=6",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
        "-map", "[v]", "-map", "3:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", "-y", str(path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace")[-900:])


def step(name: str, args: list[str]) -> tuple[bool, str]:
    proc = subprocess.run([sys.executable, str(SCRIPTS / args[0])] + args[1:],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT))
    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()
    ok = proc.returncode == 0
    detail = (out.splitlines()[-1] if out else "") or (err.splitlines()[-1] if err else "")
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail[:150]}")
    if not ok:
        print(f"         stdout: {out[:400]}")
        print(f"         stderr: {err[:400]}")
    return ok, out


def main() -> int:
    results: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="rvf_selftest_") as td:
        tmp = Path(td)
        clip = tmp / "source.mp4"
        print(f"reverse-any-video-free self-test (offline)\n  workspace: {tmp}")
        try:
            make_clip(clip)
            print(f"  generated {clip.name}: 320x180 @30fps, 6s, 2 hard cuts at frames 60/120")
        except Exception as exc:
            print(f"  [FAIL] synthetic clip generation: {exc}")
            return 1

        ok, _ = step("doctor", ["doctor.py"])
        results.append(("doctor", ok))

        probe_json = tmp / "probe.json"
        ok, _ = step("probe", ["probe.py", "--video", str(clip), "--out", str(probe_json)])
        results.append(("probe", ok))
        if ok:
            p = json.loads(probe_json.read_text(encoding="utf-8"))
            good = (p["width"], p["height"], p["fps"], p["frames"]) == (320, 180, "30/1", 180)
            print(f"  [{'PASS' if good else 'FAIL'}] probe accuracy: "
                  f"{p['width']}x{p['height']} fps={p['fps']} frames={p['frames']}")
            results.append(("probe accuracy", good))

        cuts_json = tmp / "cuts.json"
        ok, _ = step("cuts", ["cuts.py", "--video", str(clip), "--out", str(cuts_json)])
        results.append(("cuts", ok))
        if ok:
            frames = [c["frame"] for c in json.loads(cuts_json.read_text(encoding="utf-8"))["cuts"]]
            hit60 = any(abs(f - 60) <= 2 for f in frames)
            hit120 = any(abs(f - 120) <= 2 for f in frames)
            print(f"  [{'PASS' if hit60 and hit120 else 'FAIL'}] cut detection: "
                  f"detected {frames} (expected ~60 and ~120)")
            results.append(("cut detection at frame 60", hit60))
            results.append(("cut detection at frame 120", hit120))

        frames_dir = tmp / "frames"
        ok, _ = step("frames", ["frames.py", "--video", str(clip), "--range", "57,63",
                                "--out", str(frames_dir), "--sheet"])
        results.append(("frames", ok))
        if ok:
            n = len(list(frames_dir.glob("frame_*.png")))
            print(f"  [{'PASS' if n == 7 else 'FAIL'}] consecutive frames exported: {n} (expected 7)")
            results.append(("consecutive frame export", n == 7))

        report_dir = tmp / "diff"
        ok, _ = step("diff", ["diff.py", "--original", str(clip), "--render", str(clip),
                              "--out", str(report_dir), "--cuts-original", str(cuts_json),
                              "--cuts-render", str(cuts_json)])
        results.append(("diff", ok))
        if ok:
            d = json.loads((report_dir / "diff.json").read_text(encoding="utf-8"))
            clean = (not d["cuts"]["missing_cuts"] and not d["cuts"]["extra_cuts"]
                     and d["summary"]["frame_delta"] == 0)
            print(f"  [{'PASS' if clean else 'FAIL'}] identical-input diff: "
                  f"missing={d['cuts']['missing_cuts']} extra={d['cuts']['extra_cuts']} "
                  f"PSNR={d['summary']['mean_psnr']}")
            results.append(("identical-input diff", clean))
            has_report = (report_dir / "diff_report.md").is_file()
            results.append(("markdown report", has_report))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n  {passed}/{len(results)} checks passed")
    print("  self-test " + ("PASS: full free pipeline works without account or network."
                           if passed == len(results) else "FAIL: see details above."))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
