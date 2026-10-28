import argparse
import json
import sys

from . import __version__
from .audit import audit


def render(report):
    measured = report["measurements"]
    vision = report["vision"]
    motion = measured["opening_motion"]
    onset = measured["audio_onset_s"]
    cut = measured["first_cut_s"]
    lines = [f"{report['risk'].upper()} swipe risk | {report['video']}",
             f"Basis: {report['risk_basis']} (editing heuristic, not a swipe prediction)", ""]
    lines.extend(f"  {reason}" for reason in report["reasons"])
    lines += ["", "Measured:",
              f"  Opening motion (0-1.5s): {f'{motion:.4f}' if motion is not None else 'not enough frames'} (0-1 pixel difference)",
              f"  First frame: {'nearly black' if measured['first_frame_black'] else 'low detail' if measured['first_frame_low_detail'] else 'visible detail'}",
              f"  First detected cut: {f'{cut:.3f}s' if cut is not None else 'none detected'}",
              f"  First sound: {f'{onset:.3f}s' if onset is not None else measured['audio_status']} (speech not verified)",
              f"  OCR: {report['ocr']['status']}", "",
              f"Vision: {vision['provider']} / {vision['status']}"]
    if vision.get("reason"):
        lines.append(f"  {vision['reason']}")
    if vision.get("observation"):
        lines.append(f"  {vision['observation']['description']}")
        texts = vision["observation"]["on_screen_text"]
        if texts:
            lines.append(f"  Screen text (inferred): {' | '.join(texts)}")
    for frame in report["ocr"]["frames"]:
        if frame["text"]:
            lines.append(f"  OCR at {frame['time_s']:.3f}s: {frame['text']}")
    lines += ["", "Edits to try:"]
    lines.extend(f"  {index}. {fix}" for index, fix in enumerate(report["fixes"], 1))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit the actual first 1.5 seconds of a short video.")
    parser.add_argument("video", help="Local video file (up to 10 minutes)")
    parser.add_argument("--json", action="store_true", help="Print one JSON report to stdout")
    parser.add_argument("--strip", metavar="OUT.png", help="Save labeled opening and candidate frames as PNG")
    parser.add_argument("--version", action="version", version=f"hookcheck {__version__}")
    args = parser.parse_args(argv)
    try:
        report = audit(args.video, strip=args.strip)
    except (ValueError, OSError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"hookcheck: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True) if args.json else render(report))
    return 0
