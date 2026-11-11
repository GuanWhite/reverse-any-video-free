"""Shared helpers for reverse-any-video-free.

A deliberately small, offline-only toolkit: Python standard library + ffmpeg.
No network calls, no accounts, no telemetry, no HyperFrames Pro commands.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from decimal import Decimal, ROUND_DOWN
from fractions import Fraction
from pathlib import Path
from typing import Iterator

TOOLKIT = "reverse-any-video-free"
VERSION = "1.0.0"

_BIN_CACHE: dict[str, str | None] = {}


class FreeToolError(RuntimeError):
    """Raised when a local tool is missing or a free command fails."""


def find_binary(name: str) -> str | None:
    """Locate ffmpeg/ffprobe without downloading anything.

    Order: explicit env var, PATH, imageio-ffmpeg, common local install dirs.
    """
    if name in _BIN_CACHE:
        return _BIN_CACHE[name]

    env_key = "FFMPEG_BINARY" if name == "ffmpeg" else "FFPROBE_BINARY"
    exe = f"{name}.exe" if os.name == "nt" else name
    candidates: list[str] = []

    explicit = os.environ.get(env_key)
    if explicit:
        candidates.append(explicit)
    found_on_path = shutil.which(name)
    if found_on_path:
        candidates.append(found_on_path)

    if name == "ffmpeg":
        try:
            import imageio_ffmpeg  # type: ignore

            candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
        except Exception:
            pass

    home = Path.home()
    candidates += [
        str(home / ".workbuddy" / "binaries" / "ffmpeg" / exe),
        str(home / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / exe),
        str(home / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / exe),
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        f"/opt/homebrew/bin/{name}",
        f"C:/Program Files/ffmpeg/bin/{exe}",
    ]

    result = next((c for c in candidates if c and Path(c).is_file()), None)
    _BIN_CACHE[name] = result
    return result


def ffmpeg_bin() -> str:
    binary = find_binary("ffmpeg")
    if not binary:
        raise FreeToolError(
            "ffmpeg not found. Install it locally, add it to PATH, or set "
            "FFMPEG_BINARY=/absolute/path/to/ffmpeg. This toolkit never downloads binaries. "
            "Run `python scripts/doctor.py` for a full check."
        )
    return binary


def ffprobe_bin() -> str | None:
    return find_binary("ffprobe")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip()[-1200:]
        raise FreeToolError(f"Command failed ({proc.returncode}): {' '.join(cmd[:6])} ...\n{tail}")
    return proc


def probe_video(video: str | Path) -> dict:
    """Free replacement for the probe printed by `hyperframes reverse start`.

    Duration is frames / fps, never the container or audio length.
    """
    video = str(Path(video).resolve())
    if not Path(video).is_file():
        raise FreeToolError(f"Video not found: {video}")

    ffprobe = ffprobe_bin()
    if ffprobe:
        proc = run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", video])
        meta = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
        streams = meta.get("streams", [])
        v = next((s for s in streams if s.get("codec_type") == "video"), None)
        a = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not v:
            raise FreeToolError(f"No video stream in {video}")
        fps_raw = v.get("r_frame_rate") or v.get("avg_frame_rate") or "30/1"
        width, height = int(v.get("width", 0)), int(v.get("height", 0))
        nb_raw = str(v.get("nb_frames", ""))
        container_duration = float(
            v.get("duration") or meta.get("format", {}).get("duration") or 0.0
        )
        codec = v.get("codec_name", "unknown")
        pix_fmt = v.get("pix_fmt", "unknown")
        audio_codec = a.get("codec_name") if a else None
        audio_rate = a.get("sample_rate") if a else None
    else:
        # ffprobe-less fallback: parse ffmpeg's own stream header and count decoded frames.
        proc = run([ffmpeg_bin(), "-hide_banner", "-i", video, "-f", "null", "-"], check=False)
        text = proc.stderr.decode("utf-8", "replace")
        m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5}).*?([\d.]+) fps", text, re.S)
        if not m:
            raise FreeToolError(f"Cannot parse video stream header for {video}")
        width, height = int(m.group(1)), int(m.group(2))
        fps_raw = str(Fraction(m.group(3)).limit_denominator(1001))
        codec = "unknown"
        pix_fmt = "unknown"
        audio_codec = None
        audio_rate = None
        container_duration = 0.0
        fm = re.findall(r"frame=\s*(\d+)", text)
        nb_raw = fm[-1] if fm else ""

    fps = Fraction(fps_raw)
    if fps <= 0:
        raise FreeToolError(f"Invalid frame rate: {fps_raw}")
    if nb_raw.isdigit() and int(nb_raw) > 0:
        frames = int(nb_raw)
        frames_source = "nb_frames"
    else:
        frames = int(round(container_duration * float(fps)))
        frames_source = "estimated from container duration"
    if frames <= 0:
        raise FreeToolError("Could not determine frame count")

    duration = Fraction(frames, 1) / fps
    return {
        "video": video,
        "width": width,
        "height": height,
        "fps": f"{fps.numerator}/{fps.denominator}",
        "fps_float": round(float(fps), 6),
        "frames": frames,
        "duration_frames_over_fps": f"{frames}/{fps.numerator}*{fps.denominator}",
        "duration_seconds": round(float(duration), 6),
        "duration_rule": "frames / fps (NOT audio or container duration)",
        "frames_source": frames_source,
        "container_duration_seconds": round(container_duration, 6),
        "video_codec": codec,
        "pix_fmt": pix_fmt,
        "audio_codec": audio_codec,
        "audio_sample_rate": audio_rate,
        "has_audio": bool(audio_codec),
    }


def fps_of(probe: dict) -> Fraction:
    return Fraction(probe["fps"])


def frame_to_seconds(frame: int, fps: Fraction, digits: int = 6) -> str:
    """Frame-accurate time, truncated DOWN. 83 @ 30fps -> 2.766666, never 2.767."""
    quantum = Decimal(1).scaleb(-digits)
    value = (Decimal(frame) * Decimal(fps.denominator) / Decimal(fps.numerator)).quantize(
        quantum, rounding=ROUND_DOWN
    )
    return str(value)


def parse_roi(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise FreeToolError(f"ROI must be x,y,w,h (got {value!r})")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def _filtergraph(start: int | None, end: int | None, roi, size: tuple[int, int], pix: str) -> str:
    filters: list[str] = []
    if start is not None and end is not None:
        filters.append(f"select='between(n,{start},{end})'")
    if roi:
        x, y, w, h = roi
        filters.append(f"crop={w}:{h}:{x}:{y}")
    filters.append(f"scale={size[0]}:{size[1]}")
    filters.append(f"format={pix}")
    return ",".join(filters)


def _stream_frames(video: str, vf: str, pix: str, frame_size: int) -> Iterator[bytes]:
    cmd = [
        ffmpeg_bin(), "-v", "error", "-i", str(video),
        "-vf", vf, "-fps_mode", "passthrough",
        "-f", "rawvideo", "-pix_fmt", pix, "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    try:
        while True:
            buf = proc.stdout.read(frame_size)
            if len(buf) < frame_size:
                break
            yield buf
    finally:
        proc.stdout.close()
        proc.wait()


def iter_gray(
    video: str,
    *,
    start: int | None = None,
    end: int | None = None,
    roi=None,
    size: tuple[int, int] = (160, 90),
) -> Iterator[bytes]:
    vf = _filtergraph(start, end, roi, size, "gray")
    yield from _stream_frames(video, vf, "gray", size[0] * size[1])


def iter_rgb(
    video: str,
    *,
    start: int | None = None,
    end: int | None = None,
    roi=None,
    size: tuple[int, int] = (320, 180),
) -> Iterator[bytes]:
    vf = _filtergraph(start, end, roi, size, "rgb24")
    yield from _stream_frames(video, vf, "rgb24", size[0] * size[1] * 3)


def mean_abs_diff(a: bytes, b: bytes) -> float:
    if len(a) != len(b):
        raise FreeToolError("Frame buffers differ in size")
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def local_median(values: list[float], index: int, radius: int = 15) -> float:
    lo, hi = max(0, index - radius), min(len(values), index + radius + 1)
    window = sorted(values[lo:hi])
    return window[len(window) // 2] if window else 1.0


def find_cuts(
    scores: list[float],
    *,
    threshold: float = 6.0,
    min_gap: int = 3,
    min_abs: float = 8.0,
) -> list[dict]:
    """Adaptive peak detection over a full per-frame difference curve.

    Unlike ffmpeg's `select='gt(scene,x)'`, a per-frame MAD curve with a local
    baseline also exposes jump cuts and punch-ins inside a single take.
    """
    candidates: list[dict] = []
    for i in range(1, len(scores)):
        baseline = max(local_median(scores, i), 1.0)
        score = scores[i]
        if score < min_abs or score < threshold * baseline:
            continue
        if i + 1 < len(scores) and scores[i + 1] > score:
            continue
        if scores[i - 1] > score:
            continue
        candidates.append({"frame": i, "score": round(score, 3), "baseline": round(baseline, 3)})

    merged: list[dict] = []
    for cand in candidates:
        if merged and cand["frame"] - merged[-1]["frame"] <= min_gap:
            if cand["score"] > merged[-1]["score"]:
                merged[-1] = cand
        else:
            merged.append(cand)
    return merged


def find_reframes(scores: list[float], *, min_abs: float = 5.0) -> list[dict]:
    """Low-confidence hints: short bursts of change (punch-in, whip, dissolve).

    Reported separately from hard cuts because a burst is not a cut.
    """
    if not scores:
        return []
    baseline = max(sorted(scores)[len(scores) // 2], 1.0)
    hints: list[dict] = []
    i = 0
    while i < len(scores):
        if scores[i] <= max(min_abs, 2.0 * baseline):
            i += 1
            continue
        j = i
        while j < len(scores) and scores[j] > max(min_abs, 2.0 * baseline):
            j += 1
        if 2 <= j - i <= 12:
            hints.append({"start_frame": i, "end_frame": j - 1, "frames": j - i,
                          "peak": round(max(scores[i:j]), 3), "confidence": "low"})
        i = max(j, i + 1)
    return hints


def write_json(path: str | Path, data) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_stdout(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def exit_with_error(message: str) -> None:
    print(f"{TOOLKIT}: {message}", file=sys.stderr)
    raise SystemExit(2)
