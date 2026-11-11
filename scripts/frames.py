#!/usr/bin/env python3
"""Free replacement for `hyperframes measure frames --range a,b --roi ...`.

Exports CONSECUTIVE frames (sparse contact sheets miss 1-3 frame timing) and
optionally builds a contact sheet. Pillow is optional: without it, ffmpeg still
exports every frame as PNG and writes a manifest.

  python scripts/frames.py --video input.mp4 --range 58,64 --out frames/
  python scripts/frames.py --video input.mp4 --range 58,64 --roi 0,700,1920,200 --sheet
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from hf_free import (
    FreeToolError, TOOLKIT, VERSION, dump_stdout, exit_with_error,
    ffmpeg_bin, fps_of, frame_to_seconds, iter_rgb, parse_roi, probe_video,
)


def parse_range(value: str) -> tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        raise FreeToolError(f"--range must be START,END frame numbers (got {value!r})")
    return int(parts[0]), int(parts[1])


def export_with_ffmpeg(video: str, start: int, end: int, roi, out_dir: Path) -> list[str]:
    filters = [f"select='between(n,{start},{end})'"]
    if roi:
        x, y, w, h = roi
        filters.append(f"crop={w}:{h}:{x}:{y}")
    cmd = [ffmpeg_bin(), "-v", "error", "-i", video, "-vf", ",".join(filters),
           "-fps_mode", "passthrough", "-y", str(out_dir / "frame_%05d.png")]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise FreeToolError(proc.stderr.decode("utf-8", "replace")[-800:])
    files = sorted(out_dir.glob("frame_*.png"))
    return [f.name for f in files]


def export_with_pillow(video: str, start: int, end: int, roi, out_dir: Path):
    from PIL import Image  # type: ignore

    files = []
    for i, buf in enumerate(iter_rgb(video, start=start, end=end, roi=roi, size=(320, 180))):
        frame = start + i
        name = f"frame_{frame:05d}.png"
        Image.frombytes("RGB", (320, 180), buf).save(out_dir / name)
        files.append(name)
    return files


def build_sheet(out_dir: Path, names: list[str], cols: int) -> str | None:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        return None
    if not names:
        return None
    thumbs = []
    for name in names:
        im = Image.open(out_dir / name).convert("RGB")
        im.thumbnail((320, 180))
        tile = Image.new("RGB", (330, 205), "white")
        tile.paste(im, ((330 - im.width) // 2, 2))
        ImageDraw.Draw(tile).text((6, 186), name, fill="black")
        thumbs.append(tile)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 330, rows * 205), "white")
    for i, tile in enumerate(thumbs):
        sheet.paste(tile, ((i % cols) * 330, (i // cols) * 205))
    path = out_dir / "contact_sheet.png"
    sheet.save(path)
    return path.name


def main() -> int:
    ap = argparse.ArgumentParser(description="Export consecutive source frames, offline and free.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--range", required=True, help="START,END frame numbers (inclusive)")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--roi", help="Crop to x,y,w,h before export")
    ap.add_argument("--sheet", action="store_true", help="Also build a contact sheet (needs Pillow)")
    ap.add_argument("--cols", type=int, default=4, help="Contact sheet columns")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        probe = probe_video(args.video)
        fps = fps_of(probe)
        start, end = parse_range(args.range)
        if end < start or start < 0:
            raise FreeToolError("Invalid --range")
        if end - start > 600:
            raise FreeToolError("Range too long; read short consecutive strips (<= 600 frames).")
        roi = parse_roi(args.roi)
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            from PIL import Image  # noqa: F401
            names = export_with_pillow(args.video, start, end, roi, out_dir)
            exporter = "python-rgb + Pillow"
        except ImportError:
            names = export_with_ffmpeg(args.video, start, end, roi, out_dir)
            exporter = "ffmpeg png (Pillow absent)"

        sheet = build_sheet(out_dir, names, args.cols) if args.sheet else None
        manifest = {
            "toolkit": TOOLKIT,
            "version": VERSION,
            "video": probe["video"],
            "fps": probe["fps"],
            "range_frames": [start, end],
            "roi": list(roi) if roi else None,
            "exporter": exporter,
            "frames": [
                {"frame": start + i, "time_seconds": frame_to_seconds(start + i, fps), "file": name}
                for i, name in enumerate(names)
            ],
            "contact_sheet": sheet,
            "note": "Read these frames in order: arrival direction, exits, dissolves and 1-frame flashes.",
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (FreeToolError, ValueError) as exc:
        exit_with_error(str(exc))

    print(f"{len(manifest['frames'])} frame(s) -> {out_dir}  ({exporter})")
    if sheet:
        print(f"contact sheet -> {out_dir / sheet}")
    if args.json:
        dump_stdout(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
