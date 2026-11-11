#!/usr/bin/env python3
"""Free replacement for `hyperframes measure cuts` and `measure events --roi`.

Builds a full per-frame difference curve (not a sparse scene score), then finds
hard cuts with an adaptive local baseline and reports short bursts (jump cuts,
punch-ins, dissolves) separately as low-confidence hints.

  python scripts/cuts.py --video input.mp4 --out cuts.json
  python scripts/cuts.py --video input.mp4 --roi 0,720,1920,180 --out captions.json
"""
from __future__ import annotations

import argparse
from pathlib import Path

from hf_free import (
    FreeToolError, TOOLKIT, VERSION, dump_stdout, exit_with_error,
    find_cuts, find_reframes, fps_of, frame_to_seconds, iter_gray,
    mean_abs_diff, parse_roi, probe_video, write_json,
)


def parse_range(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.split(",")
    if len(parts) != 2:
        raise FreeToolError(f"--range must be START,END in frame numbers (got {value!r})")
    return int(parts[0]), int(parts[1])


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect cuts and band events, offline and free.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", help="Write JSON result here")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--roi", help="Only measure x,y,w,h (e.g. a caption band)")
    ap.add_argument("--range", dest="frame_range", help="Only analyse frames START,END")
    ap.add_argument("--threshold", type=float, default=6.0,
                    help="Peak / local-baseline ratio for a hard cut (default 6.0)")
    ap.add_argument("--min-abs", type=float, default=8.0,
                    help="Minimum absolute mean pixel difference (default 8.0)")
    ap.add_argument("--min-gap", type=int, default=3, help="Merge peaks this close, in frames")
    ap.add_argument("--score-curve", help="Also write the full per-frame score curve as CSV")
    ap.add_argument("--size", default="160x90", help="Analysis downscale WxH (default 160x90)")
    args = ap.parse_args()

    try:
        probe = probe_video(args.video)
        fps = fps_of(probe)
        roi = parse_roi(args.roi)
        rng = parse_range(args.frame_range)
        width, height = (int(x) for x in args.size.lower().split("x"))

        scores: list[float] = []
        previous = None
        start = rng[0] if rng else None
        end = rng[1] if rng else None
        for buf in iter_gray(args.video, start=start, end=end, roi=roi, size=(width, height)):
            if previous is not None:
                scores.append(mean_abs_diff(previous, buf))
            previous = buf

        cuts = find_cuts(scores, threshold=args.threshold,
                         min_gap=args.min_gap, min_abs=args.min_abs)
        offset = rng[0] + 1 if rng else 1
        # scores[i] is the difference between frame (offset+i) and its predecessor.
        for cut in cuts:
            frame = offset + cut["frame"]
            cut["frame"] = frame
            cut["time_seconds"] = frame_to_seconds(frame, fps)
            cut["time_exact"] = f"{frame}/{probe['fps']}"
        reframes = find_reframes(scores, min_abs=args.min_abs)
        for hint in reframes:
            hint["start_frame"] += offset
            hint["end_frame"] += offset

        result = {
            "toolkit": TOOLKIT,
            "version": VERSION,
            "video": probe["video"],
            "fps": probe["fps"],
            "frames_analyzed": len(scores) + 1,
            "analysis_size": f"{width}x{height}",
            "roi": list(roi) if roi else None,
            "frame_range": list(rng) if rng else None,
            "threshold": args.threshold,
            "min_abs": args.min_abs,
            "cuts": cuts,
            "reframe_hints": reframes,
            "usage_note": (
                "Use cut.frame for timing; write time as frame / fps truncated DOWN to 6 decimals. "
                "Reframe hints are not cuts: verify them with consecutive frames before using them."
            ),
        }
        if roi:
            result["usage_note"] += (
                " ROI mode measures a pixel band: use these frames for caption switch times, "
                "not speech-to-text timestamps."
            )
        if args.score_curve:
            csv = Path(args.score_curve)
            csv.parent.mkdir(parents=True, exist_ok=True)
            csv.write_text("frame,mean_abs_diff\n" + "".join(
                f"{offset + i},{s:.4f}\n" for i, s in enumerate(scores)), encoding="utf-8")
            result["score_curve"] = str(csv)
    except (FreeToolError, ValueError) as exc:
        exit_with_error(str(exc))

    if args.out:
        write_json(args.out, result)
    if args.json or not args.out:
        dump_stdout(result)
    else:
        print(f"{len(result['cuts'])} cuts, {len(result['reframe_hints'])} reframe hints "
              f"over {result['frames_analyzed']} frames -> {args.out}")
        for cut in result["cuts"]:
            print(f"  frame {cut['frame']:>6}  t={cut['time_seconds']:>10}s  score={cut['score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
