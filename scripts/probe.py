#!/usr/bin/env python3
"""Free replacement for the probe printed by `hyperframes reverse start`.

Prints the exact canvas, fractional frame rate and frame-derived duration that
the root composition must use. Requires only a local ffmpeg/ffprobe binary.

  python scripts/probe.py --video input.mp4 --out probe.json
"""
from __future__ import annotations

import argparse

from hf_free import FreeToolError, TOOLKIT, VERSION, dump_stdout, exit_with_error, probe_video, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe a video without any account or network access.")
    ap.add_argument("--video", required=True, help="Source video file")
    ap.add_argument("--out", help="Write the JSON probe to this path")
    ap.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = ap.parse_args()

    try:
        probe = probe_video(args.video)
    except FreeToolError as exc:
        exit_with_error(str(exc))

    probe["toolkit"] = TOOLKIT
    probe["version"] = VERSION
    probe["root_composition"] = {
        "data-width": probe["width"],
        "data-height": probe["height"],
        "data-fps": probe["fps"],
        "data-duration": probe["duration_seconds"],
        "warning": "Do not use a default 1920x1080/30fps canvas or the container duration.",
    }
    if args.out:
        write_json(args.out, probe)
        print(f"probe written to {args.out}")
    if args.json or not args.out:
        dump_stdout(probe)
    else:
        print(f"{probe['width']}x{probe['height']}  fps={probe['fps']}  "
              f"frames={probe['frames']}  duration={probe['duration_seconds']}s  "
              f"audio={probe['audio_codec'] or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
