from pathlib import Path
import time

from . import __version__
from .media import audio_onset, extract, ocr, probe, scan, write_strip
from .vision import analyze


def verdict(measurements, vision):
    reasons = []
    fixes = []
    motion = measurements["opening_motion"]
    score = 0
    if measurements["first_frame_black"]:
        score += 3
        reasons.append("The first frame is nearly black.")
        fixes.append("Remove the black lead-in and open on a readable subject.")
    elif measurements["first_frame_low_detail"]:
        score += 2
        reasons.append("The first frame has very little visual detail; it may be a blank card.")
    if motion is None:
        score += 1
        reasons.append("The clip is too short to measure opening motion.")
    elif motion < 0.005:
        score += 2
        reasons.append("The opening barely changes across the first 1.5 seconds.")
    elif motion < 0.015:
        score += 1
        reasons.append("The opening has limited visual change.")
    else:
        reasons.append("Visual activity is present from the opening.")
    onset = measurements["audio_onset_s"]
    if onset is None:
        score += 1
        reasons.append("No sound onset was detected; the visual hook must work alone.")
    elif onset > 0.5:
        score += 1
        reasons.append(f"The first detected sound starts at {onset:.2f}s; speech is not verified.")
        fixes.append(f"If speech belongs at the start, remove the {onset:.2f}s audio lead-in.")
    observation = vision.get("observation")
    if observation:
        reasons.insert(0, observation["description"])
        if observation["mostly_talking_or_posing"] and not observation["action_visible_at_start"]:
            score = max(2, score)
            fixes.insert(0, "Open on the problem or action itself before the talking or announcement.")
        elif observation["action_visible_at_start"] and not measurements["first_frame_black"]:
            score = max(0, score - 2)
        else:
            score = max(1, score)
    candidate = measurements["candidate_start_s"]
    if candidate is not None and (not observation or observation["candidate_action_visible"] is not False):
        description = observation.get("candidate_description") if observation else None
        detail = f" Vision sees: {description}" if description else " This is a motion-based candidate, not a verified story beat."
        fixes.insert(0, f"Try starting at {candidate:.3f}s, where a later 0.5s window has more visual activity.{detail} Check sentence continuity before cutting.")
    if not fixes:
        fixes.append("Show the concrete problem or result in frame zero; compare both openings in your platform analytics."
                     if score else "Keep frame zero active and readable; validate it with stayed-to-watch analytics.")
    return ("high" if score >= 2 else "medium" if score == 1 else "low"), reasons, fixes[:3]


def audit(video, strip=None, vision_provider=None):
    started = time.perf_counter()
    path = Path(video).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Video file does not exist or is not a regular file.")
    if strip is not None and Path(strip).expanduser().resolve() == path:
        raise ValueError("The strip output must not overwrite the input video.")
    info = probe(path)
    frames = [extract(path, stamp, info["video_stream_index"]) for stamp in (0.0, 0.5, 1.0, 1.5)
              if stamp < info["duration_s"]]
    measurements = scan(path, info, frames[0])
    onset, audio_status = audio_onset(path, info)
    measurements.update({"audio_onset_s": onset, "audio_status": audio_status,
                         "silence_threshold_db": -35, "voice_onset_s": None,
                         "voice_status": "not_verified"})
    candidate = []
    if measurements["candidate_start_s"] is not None:
        start = measurements["candidate_start_s"]
        candidate = [extract(path, stamp, info["video_stream_index"]) for stamp in (start, start + 0.5)
                     if stamp < info["duration_s"]]
    text = ocr(frames)
    vision = analyze(frames, candidate, vision_provider)
    risk, reasons, fixes = verdict(measurements, vision)
    if strip is not None:
        write_strip(frames + candidate, Path(strip).expanduser())
    return {"schema_version": 1, "version": __version__, "video": path.name, "media": info,
            "risk": risk, "risk_basis": "heuristic_with_vision" if vision["status"] == "inferred" else "measurements_only",
            "reasons": reasons, "fixes": fixes, "measurements": measurements, "vision": vision, "ocr": text,
            "frames": [{"time_s": frame.time_s, "role": "opening", "timing": "seek_target"} for frame in frames]
                      + [{"time_s": frame.time_s, "role": "candidate", "timing": "seek_target"} for frame in candidate],
            "elapsed_s": round(time.perf_counter() - started, 3),
            "limitations": ["Risk is an uncalibrated editing heuristic, not a predicted swipe percentage.",
                            "Sound onset is not speech recognition; music or noise can trigger it.",
                            "Pixel change includes camera moves, edits and flashes; it does not establish meaning.",
                            "Frame labels are seek targets; variable frame rates can shift the decoded frame."]}
