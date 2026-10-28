from dataclasses import dataclass
from io import BytesIO
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageStat


SCAN_FPS = 8
FRAME_SIZE = (160, 90)
MAX_DURATION = 600


@dataclass
class Frame:
    time_s: float
    image: bytes


def run(args, **kwargs):
    try:
        result = subprocess.run(args, stderr=subprocess.PIPE, timeout=120, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Media processing exceeded 120 seconds.") from exc
    if result.returncode:
        raise ValueError("Could not decode media. Check the file and your ffmpeg installation.")
    return result


def probe(path):
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise ValueError(f"{tool} is required. Install ffmpeg and add it to PATH.")
    data = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", str(path)], stdout=subprocess.PIPE).stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ValueError("The file has no video stream.")
    duration = float(video.get("duration") or data.get("format", {}).get("duration") or 0)
    if not math.isfinite(duration) or not 0 < duration <= MAX_DURATION:
        raise ValueError("Use a video with a known duration between 0 and 600 seconds.")
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    audio_offset = float(audio.get("start_time") or 0) - float(video.get("start_time") or 0) if audio else 0
    return {"duration_s": round(duration, 4), "width": video["width"], "height": video["height"],
            "video_stream_index": video["index"],
            "has_audio": audio is not None, "audio_offset_s": audio_offset}


def extract(path, time_s, stream):
    result = run(["ffmpeg", "-v", "error", "-nostdin", "-ss", str(time_s), "-i", str(path),
                  "-map", f"0:{stream}", "-frames:v", "1", "-vf", "scale=512:512:force_original_aspect_ratio=decrease,setsar=1",
                  "-f", "image2pipe", "-c:v", "mjpeg", "pipe:1"], stdout=subprocess.PIPE)
    if not result.stdout:
        raise ValueError(f"No video frame could be decoded at {time_s:.3f}s.")
    return Frame(time_s, result.stdout)


def scan(path, info, first_frame):
    with tempfile.TemporaryFile() as raw:
        result = run(["ffmpeg", "-hide_banner", "-loglevel", "info", "-nostdin", "-i", str(path),
                      "-map", f"0:{info['video_stream_index']}", "-an", "-t", str(MAX_DURATION),
                      "-vf", "setpts=PTS-STARTPTS,scale=160:90,format=gray,scdet=threshold=12,fps=8:start_time=0",
                      "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], stdout=raw)
        raw.seek(0)
        previous = None
        changes = []
        first = Image.open(BytesIO(first_frame.image)).convert("L").resize(FRAME_SIZE)
        while True:
            pixels = raw.read(FRAME_SIZE[0] * FRAME_SIZE[1])
            if not pixels:
                break
            if len(pixels) != FRAME_SIZE[0] * FRAME_SIZE[1]:
                raise ValueError("Incomplete decoded video frame.")
            current = Image.frombytes("L", FRAME_SIZE, pixels)
            if previous is not None:
                delta = ImageStat.Stat(ImageChops.difference(current, previous)).mean[0] / 255
                changes.append(delta)
            previous = current
    hook_changes = changes[:12]
    motion = sum(hook_changes) / len(hook_changes) if hook_changes else None
    stats = ImageStat.Stat(first)
    black = sum(first.histogram()[:21]) / (FRAME_SIZE[0] * FRAME_SIZE[1]) >= 0.98
    flat = stats.stddev[0] < 4
    window = 4
    candidates = []
    for index in range(12, len(changes) - window + 1):
        start = (index + 1) / SCAN_FPS
        activity = sum(changes[index:index + window]) / window
        candidates.append((activity, start))
    best_activity, best_start = max(candidates, default=(0.0, None), key=lambda pair: pair[0])
    candidate = best_start if best_activity >= max(0.008, (motion or 0) * 1.5) else None
    matches = re.findall(r"scdet[^\n]*lavfi\.scd\.score: [\d.]+, lavfi\.scd\.time: ([\d.]+)",
                         result.stderr.decode(errors="replace"))
    return {"opening_motion": round(motion, 6) if motion is not None else None,
            "motion_sample_fps": SCAN_FPS, "first_frame_black": black,
            "first_frame_low_detail": flat, "first_frame_luma": round(stats.mean[0], 2),
            "first_cut_s": float(matches[0]) if matches else None,
            "scene_threshold": 12, "candidate_start_s": candidate,
            "candidate_motion": round(best_activity, 6) if candidate is not None else None,
            "candidate_resolution_s": 1 / SCAN_FPS, "scanned_duration_s": info["duration_s"]}


def audio_onset(path, info):
    if not info["has_audio"]:
        return None, "no_audio_stream"
    offset = info["audio_offset_s"]
    result = run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:a:0", "-vn",
                  "-t", str(MAX_DURATION), "-af", f"asetpts=PTS-STARTPTS,atrim=start={max(0, -offset)},asetpts=PTS-STARTPTS,silencedetect=noise=-35dB:d=0.05",
                  "-f", "null", "-"], stdout=subprocess.DEVNULL)
    events = re.findall(r"silence_(start|end): ([\d.eE+-]+)", result.stderr.decode(errors="replace"))
    if events and events[0][0] == "start" and float(events[0][1]) <= 0.02:
        end = next((float(value) for kind, value in events if kind == "end"), None)
        if end is None or end >= info["duration_s"] - 0.02:
            return None, "silent_track"
        onset = end + max(0, offset)
        return (round(onset, 4), "sound_detected") if onset < info["duration_s"] else (None, "silent_track")
    if max(0, offset) >= info["duration_s"]:
        return None, "silent_track"
    return round(max(0, offset), 4), "sound_detected"


def ocr(frames):
    if not shutil.which("tesseract"):
        return {"status": "unavailable", "reason": "Install tesseract for optional local OCR.", "frames": []}
    results = []
    try:
        with tempfile.TemporaryDirectory() as folder:
            for index, frame in enumerate(frames):
                path = Path(folder) / f"{index}.jpg"
                path.write_bytes(frame.image)
                result = run(["tesseract", str(path), "stdout", "--psm", "11"], stdout=subprocess.PIPE)
                results.append({"time_s": frame.time_s, "text": result.stdout.decode(errors="replace").strip()})
    except (ValueError, OSError):
        return {"status": "unavailable", "reason": "Local OCR failed.", "frames": []}
    return {"status": "measured", "frames": results}


def write_strip(frames, path):
    width, height = 240, 440
    canvas = Image.new("RGB", (width * len(frames), height), "#10131a")
    draw = ImageDraw.Draw(canvas)
    for index, frame in enumerate(frames):
        picture = Image.open(BytesIO(frame.image)).convert("RGB")
        picture.thumbnail((width, height - 32))
        canvas.paste(picture, (index * width + (width - picture.width) // 2, 30 + (height - 32 - picture.height) // 2))
        draw.text((index * width + 10, 10), f"{frame.time_s:.3f}s", fill="white")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".hookcheck-", suffix=".png", delete=False) as output:
            temporary = Path(output.name)
            canvas.save(output, format="PNG")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
