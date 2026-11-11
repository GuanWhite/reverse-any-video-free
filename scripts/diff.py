#!/usr/bin/env python3
"""Free replacement for `hyperframes diff <original> <render>`.

Reports missing/extra cuts, duration and frame deltas, an estimated audio
offset, per-frame PSNR/SSIM, stretches with missing content, and side-by-side
images of the worst moments. Pure local ffmpeg + Python.

  python scripts/diff.py --original src.mp4 --render out.mp4 --out report/
"""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
import tempfile
from array import array
from pathlib import Path

from hf_free import (
    FreeToolError, TOOLKIT, VERSION, dump_stdout, exit_with_error,
    ffmpeg_bin, fps_of, frame_to_seconds, probe_video, run, write_json,
)

SCRIPTS = Path(__file__).resolve().parent


def detect_cuts(video: str, tmp: Path, tag: str) -> tuple[list[int], dict]:
    out = tmp / f"cuts_{tag}.json"
    cmd = [sys.executable, str(SCRIPTS / "cuts.py"), "--video", video, "--out", str(out)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise FreeToolError(f"cuts detection failed for {tag}: "
                            f"{proc.stderr.decode('utf-8', 'replace')[-500:]}")
    import json
    data = json.loads(out.read_text(encoding="utf-8"))
    return [c["frame"] for c in data["cuts"]], data


def compare_cuts(original: list[int], rendered: list[int], tolerance: int = 1) -> dict:
    missing = [f for f in original if not any(abs(f - g) <= tolerance for g in rendered)]
    extra = [g for g in rendered if not any(abs(f - g) <= tolerance for f in original)]
    matched = [f for f in original if f not in missing]
    return {
        "original": original, "rendered": rendered,
        "matched": matched, "missing_cuts": missing, "extra_cuts": extra,
        "tolerance_frames": tolerance,
    }


def _quality(video_a: str, video_b: str, probe: dict, tmp: Path, metric: str) -> list[float]:
    stats_name = f"{metric}.log"
    stats = tmp / stats_name
    w, h = probe["width"], probe["height"]
    fr = probe["fps_float"]
    common = f"settb=AVTB,setpts=N/({fr}*TB),scale={w}:{h},format=yuv420p"
    graph = f"[0:v]{common}[a];[1:v]{common}[b];[a][b]{metric}=stats_file={stats_name}"
    cmd = [ffmpeg_bin(), "-v", "error", "-i", video_a, "-i", video_b,
           "-filter_complex", graph, "-an", "-f", "null", "-"]
    # cwd=tmp keeps stats_file a plain relative name (no Windows drive colon in the filtergraph).
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(tmp))
    if proc.returncode != 0 or not stats.is_file():
        return []
    key = "psnr_avg" if metric == "psnr" else "All"
    values = []
    for line in stats.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(rf"{key}:([^\s]+)", line)
        if not m:
            continue
        token = m.group(1)
        try:
            values.append(float("inf") if token in ("inf", "-inf") else float(token))
        except ValueError:
            values.append(float("nan"))
    return values


def _envelope(video: str, rate: int = 8000, hop: int = 80) -> list[float] | None:
    proc = subprocess.run(
        [ffmpeg_bin(), "-v", "error", "-i", video, "-vn", "-ac", "1",
         "-ar", str(rate), "-f", "s16le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if proc.returncode != 0 or len(proc.stdout) < hop * 2:
        return None
    pcm = array("h")
    pcm.frombytes(proc.stdout[: len(proc.stdout) // 2 * 2])
    env = []
    for i in range(0, len(pcm) - hop, hop):
        chunk = pcm[i:i + hop]
        env.append(math.sqrt(sum(v * v for v in chunk) / hop))
    if not env or max(env) == 0:
        return None
    mean = sum(env) / len(env)
    var = sum((v - mean) ** 2 for v in env) / len(env)
    if var == 0:
        return None
    sd = math.sqrt(var)
    return [(v - mean) / sd for v in env]


def audio_offset(a: str, b: str, max_seconds: float = 2.0) -> dict | None:
    ea, eb = _envelope(a), _envelope(b)
    if not ea or not eb:
        return None
    max_lag = min(int(max_seconds * 100), len(ea) // 4, len(eb) // 4)
    best, best_score = 0, -2.0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x, y = ea[lag:], eb[:len(eb) - lag] if lag else eb
        else:
            x, y = ea[:len(ea) + lag], eb[-lag:]
        n = min(len(x), len(y))
        if n < 50:
            continue
        score = sum(x[i] * y[i] for i in range(n)) / n
        if score > best_score:
            best, best_score = lag, score
    return {"offset_seconds": round(best * 0.01, 3),
            "correlation": round(best_score, 4),
            "resolution_seconds": 0.01,
            "method": "100 Hz loudness-envelope cross-correlation (approximation)"}


def export_frames(video: str, frames: list[int], out_dir: Path, prefix: str) -> dict[int, str]:
    if not frames:
        return {}
    out_dir.mkdir(parents=True, exist_ok=True)
    expr = "+".join(f"eq(n\\,{f})" for f in frames)
    cmd = [ffmpeg_bin(), "-v", "error", "-i", video, "-vf", f"select='{expr}'",
           "-fps_mode", "passthrough", "-y", str(out_dir / f"{prefix}_%03d.png")]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return {}
    files = sorted(out_dir.glob(f"{prefix}_*.png"))
    return dict(zip(frames, [f.name for f in files]))


def side_by_side(a_dir: Path, b_dir: Path, a_files: dict, b_files: dict,
                 frames: list[int], out_dir: Path) -> dict[int, str]:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        return {}
    result = {}
    for f in frames:
        if f not in a_files or f not in b_files:
            continue
        left = Image.open(a_dir / a_files[f]).convert("RGB")
        right = Image.open(b_dir / b_files[f]).convert("RGB")
        left.thumbnail((480, 270))
        right.thumbnail((480, 270))
        canvas = Image.new("RGB", (left.width + right.width + 12, max(left.height, right.height) + 24), "white")
        canvas.paste(left, (0, 24))
        canvas.paste(right, (left.width + 12, 24))
        ImageDraw.Draw(canvas).text((6, 5), f"frame {f}   original | yours", fill="black")
        name = f"sbs_{f:06d}.png"
        canvas.save(out_dir / name)
        result[f] = name
    return result


def missing_segments(psnr: list[float], threshold_db: float = 22.0) -> list[dict]:
    segments, start = [], None
    for i, value in enumerate(psnr):
        bad = not math.isinf(value) and not math.isnan(value) and value < threshold_db
        if bad and start is None:
            start = i
        elif not bad and start is not None:
            if i - start >= 2:
                segments.append({"start_frame": start + 1, "end_frame": i,
                                 "frames": i - start, "reason": "PSNR below threshold"})
            start = None
    if start is not None and len(psnr) - start >= 2:
        segments.append({"start_frame": start + 1, "end_frame": len(psnr),
                         "frames": len(psnr) - start, "reason": "PSNR below threshold"})
    return segments


def markdown_report(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# Reverse diff report (free toolkit)",
        "",
        f"- Toolkit: `{TOOLKIT} {VERSION}` — no account, no network, no credits",
        f"- Original: `{result['original']['video']}`",
        f"- Render: `{result['render']['video']}`",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Canvas | {s['canvas_original']} vs {s['canvas_render']} |",
        f"| FPS | {s['fps_original']} vs {s['fps_render']} |",
        f"| Frames | {s['frames_original']} vs {s['frames_render']} |",
        f"| Duration (frames/fps) | {s['duration_original']}s vs {s['duration_render']}s |",
        f"| Missing cuts | {len(result['cuts']['missing_cuts'])} |",
        f"| Extra cuts | {len(result['cuts']['extra_cuts'])} |",
        f"| Mean PSNR | {s['mean_psnr']} dB |",
        f"| Mean SSIM | {s['mean_ssim']} |",
        f"| Audio offset | {s['audio_offset']} |",
        f"| Missing-content stretches | {len(result['missing_segments'])} |",
        "",
        "## Cuts",
        "",
        f"- Original frames: `{result['cuts']['original']}`",
        f"- Render frames: `{result['cuts']['rendered']}`",
        f"- Missing: `{result['cuts']['missing_cuts']}`  Extra: `{result['cuts']['extra_cuts']}`",
        "",
        "## Worst moments",
        "",
        "| Frame | Time (s) | PSNR (dB) | Side-by-side |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["worst_moments"]:
        img = item.get("side_by_side")
        cell = f"![frame {item['frame']}]({img})" if img else "frames exported separately"
        lines.append(f"| {item['frame']} | {item['time_seconds']} | {item['psnr_db']} | {cell} |")
    lines += [
        "",
        "## Limits of this check",
        "",
        "- PSNR/SSIM are pixel metrics: film grain, compression noise and substituted fonts lower the score even when the look is right.",
        "- Audio offset is a loudness-envelope approximation (10 ms resolution), not sample-accurate.",
        "- Cut comparison uses a 1-frame tolerance; verify reframe hints by reading consecutive frames.",
        "- Fix what the report names and that you can see, then render and diff ONCE more, then stop.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare a rebuild against its source, offline and free.")
    ap.add_argument("--original", required=True)
    ap.add_argument("--render", required=True)
    ap.add_argument("--out", required=True, help="Report directory")
    ap.add_argument("--cuts-original", help="Optional precomputed cuts.json for the original")
    ap.add_argument("--cuts-render", help="Optional precomputed cuts.json for the render")
    ap.add_argument("--worst", type=int, default=5, help="How many worst frames to export")
    ap.add_argument("--no-audio-offset", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        src = probe_video(args.original)
        dst = probe_video(args.render)
        fps = fps_of(src)
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="rvf_diff_") as td:
            tmp = Path(td)
            if args.cuts_original:
                import json
                src_cuts = [c["frame"] for c in json.loads(
                    Path(args.cuts_original).read_text(encoding="utf-8"))["cuts"]]
            else:
                src_cuts, _ = detect_cuts(args.original, tmp, "original")
            if args.cuts_render:
                import json
                dst_cuts = [c["frame"] for c in json.loads(
                    Path(args.cuts_render).read_text(encoding="utf-8"))["cuts"]]
            else:
                dst_cuts, _ = detect_cuts(args.render, tmp, "render")

            psnr = _quality(args.original, args.render, src, tmp, "psnr")
            ssim = _quality(args.original, args.render, src, tmp, "ssim")
            finite_p = [v for v in psnr if math.isfinite(v) and not math.isnan(v)]
            finite_s = [v for v in ssim if math.isfinite(v) and not math.isnan(v)]
            mean_psnr = "inf (pixel-identical)" if len(finite_p) < len(psnr) and psnr else (
                round(sum(finite_p) / len(finite_p), 3) if finite_p else "n/a")
            mean_ssim = round(sum(finite_s) / len(finite_s), 5) if finite_s else "n/a"

            scored = [(i + 1, (v if math.isfinite(v) else 999.0)) for i, v in enumerate(psnr)]
            worst_frames = [f for f, _ in sorted(scored, key=lambda x: x[1])[:args.worst]]
            a_dir, b_dir = out_dir / "original", out_dir / "yours"
            a_files = export_frames(args.original, worst_frames, a_dir, "orig")
            b_files = export_frames(args.render, worst_frames, b_dir, "yours")
            sbs = side_by_side(a_dir, b_dir, a_files, b_files, worst_frames, out_dir)
            worst = [
                {"frame": f,
                 "time_seconds": frame_to_seconds(f, fps),
                 "psnr_db": ("inf" if f - 1 < len(psnr) and math.isinf(psnr[f - 1])
                             else round(scored[f - 1][1], 3) if f - 1 < len(scored) else "n/a"),
                 "side_by_side": sbs.get(f)}
                for f in worst_frames
            ]
            offset = None if args.no_audio_offset or not (src["has_audio"] and dst["has_audio"]) \
                else audio_offset(args.original, args.render)

            result = {
                "toolkit": TOOLKIT, "version": VERSION,
                "account_required": False, "network_required": False,
                "original": src, "render": dst,
                "summary": {
                    "canvas_original": f"{src['width']}x{src['height']}",
                    "canvas_render": f"{dst['width']}x{dst['height']}",
                    "fps_original": src["fps"], "fps_render": dst["fps"],
                    "frames_original": src["frames"], "frames_render": dst["frames"],
                    "frame_delta": dst["frames"] - src["frames"],
                    "duration_original": src["duration_seconds"],
                    "duration_render": dst["duration_seconds"],
                    "duration_delta_seconds": round(dst["duration_seconds"] - src["duration_seconds"], 6),
                    "mean_psnr": mean_psnr, "mean_ssim": mean_ssim,
                    "audio_offset": offset,
                },
                "cuts": compare_cuts(src_cuts, dst_cuts),
                "missing_segments": missing_segments(psnr),
                "worst_moments": worst,
                "frames_scored": len(psnr),
                "notes": [
                    "Duration is frames / fps, not audio or container length.",
                    "Fix visible findings, then render and diff once more, then stop.",
                ],
            }
        write_json(out_dir / "diff.json", result)
        (out_dir / "diff_report.md").write_text(markdown_report(result), encoding="utf-8")
    except (FreeToolError, ValueError, OSError) as exc:
        exit_with_error(str(exc))

    print(f"diff -> {out_dir / 'diff_report.md'}")
    print(f"  missing cuts: {result['cuts']['missing_cuts']}  extra cuts: {result['cuts']['extra_cuts']}")
    print(f"  mean PSNR: {result['summary']['mean_psnr']}  mean SSIM: {result['summary']['mean_ssim']}")
    if args.json:
        dump_stdout(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
