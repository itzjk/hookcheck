import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hookcheck.audit import audit
from hookcheck.media import write_strip
from PIL import Image


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        cls.static = cls.make_video("static.mp4", "smptebars=size=180x320:rate=24:duration=5")
        cls.moving = cls.make_video("moving.mp4", "testsrc2=size=180x320:rate=24:duration=5")
        cls.delayed = cls.root / "delayed.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
            "smptebars=size=180x320:rate=24:duration=3", "-f", "lavfi", "-i",
            "testsrc2=size=180x320:rate=24:duration=3", "-f", "lavfi", "-i",
            "sine=frequency=440:duration=5", "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a]adelay=1000:all=1[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(cls.delayed)
        ], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    @classmethod
    def make_video(cls, name, source, audio=True):
        path = cls.root / name
        args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source]
        if audio:
            args += ["-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-shortest"]
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
        subprocess.run(args, check=True, capture_output=True)
        return path

    def run_audit(self, path, **kwargs):
        with patch.dict(os.environ, {"HOOKCHECK_PROVIDER": "none"}):
            return audit(path, **kwargs)

    def test_real_video_static_vs_motion_verdict(self):
        still = self.run_audit(self.static)
        moving = self.run_audit(self.moving)
        self.assertEqual(still["risk"], "high")
        self.assertEqual(moving["risk"], "low")
        self.assertLess(still["measurements"]["opening_motion"], moving["measurements"]["opening_motion"])
        self.assertEqual(still["vision"]["status"], "disabled")

    def test_search_finds_later_action_cut_and_audio(self):
        result = self.run_audit(self.delayed)
        measurements = result["measurements"]
        self.assertAlmostEqual(measurements["first_cut_s"], 3, delta=0.1)
        self.assertAlmostEqual(measurements["audio_onset_s"], 1, delta=0.1)
        self.assertGreaterEqual(measurements["candidate_start_s"], 3)
        self.assertLess(measurements["candidate_start_s"], 5)
        self.assertTrue(any("Try starting at" in fix for fix in result["fixes"]))
        self.assertIsNone(measurements["voice_onset_s"])

    def test_black_silent_and_short_clips(self):
        black = self.make_video("black.mp4", "color=black:size=180x320:rate=24:duration=0.041667", False)
        result = self.run_audit(black)
        self.assertTrue(result["measurements"]["first_frame_black"])
        self.assertIsNone(result["measurements"]["audio_onset_s"])
        self.assertEqual(result["risk"], "high")
        self.assertEqual([frame["time_s"] for frame in result["frames"]], [0.0])

    def test_silent_audio_track_is_not_onset_at_zero(self):
        path = self.root / "silent.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(self.static),
                        "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                        "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "copy",
                        str(path)], check=True, capture_output=True)
        self.assertIsNone(self.run_audit(path)["measurements"]["audio_onset_s"])

    def test_only_first_source_frame_is_black(self):
        path = self.root / "one-black-frame.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=black:size=180x320:rate=24:duration=0.041667", "-f", "lavfi", "-i",
                        "testsrc2=size=180x320:rate=24:duration=2", "-filter_complex",
                        "[0:v][1:v]concat=n=2:v=1:a=0", "-c:v", "libx264", str(path)],
                       check=True, capture_output=True)
        self.assertTrue(self.run_audit(path)["measurements"]["first_frame_black"])

    def test_audio_stream_offset_is_preserved(self):
        path = self.root / "offset.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(self.static), "-itsoffset", "1",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", str(path)], check=True, capture_output=True)
        self.assertAlmostEqual(self.run_audit(path)["measurements"]["audio_onset_s"], 1, delta=0.1)

    def test_reject_overwrite_corrupt_and_missing_ffmpeg(self):
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.run_audit(self.static, strip=self.static)
        corrupt = self.root / "corrupt.mp4"
        corrupt.write_bytes(b"not a video")
        with self.assertRaisesRegex(ValueError, "decode"):
            self.run_audit(corrupt)
        with patch("hookcheck.media.shutil.which", return_value=None), self.assertRaisesRegex(ValueError, "required"):
            self.run_audit(self.static)

    def test_cli_rejects_strip_aliases_without_changing_input(self):
        env = dict(os.environ, HOOKCHECK_PROVIDER="none")
        for alias in ("same_path", "symlink", "hardlink", "symlink_to_hardlink"):
            for json_output in (False, True):
                with self.subTest(alias=alias, json=json_output), tempfile.TemporaryDirectory() as folder:
                    source = Path(folder) / "video.mp4"
                    shutil.copyfile(self.moving, source)
                    before = source.read_bytes()
                    strip = Path(folder) / "strip.png"
                    if alias == "same_path":
                        strip = source
                    elif alias == "symlink":
                        strip.symlink_to(source)
                    elif alias == "hardlink":
                        os.link(source, strip)
                    else:
                        link = Path(folder) / "linked.mp4"
                        os.link(source, link)
                        strip.symlink_to(link)
                    args = [sys.executable, "-m", "hookcheck", str(source), "--strip", str(strip)]
                    result = subprocess.run(args + (["--json"] if json_output else []),
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(source.read_bytes(), before, "The input video was changed")
                    self.assertEqual(strip.read_bytes(), before)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    if json_output:
                        self.assertIn("overwrite", json.loads(result.stdout)["error"])
                        self.assertEqual(result.stderr, "")
                    else:
                        self.assertEqual(result.stdout, "")
                        self.assertIn("overwrite", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_strip_link_created_during_audit_cannot_modify_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "video.mp4"
            shutil.copyfile(self.moving, source)
            before = source.read_bytes()
            strip = Path(folder) / "strip.png"

            def link_during_analysis(frames, candidate, provider):
                os.link(source, strip)
                return {"status": "disabled"}

            with patch("hookcheck.audit.analyze", side_effect=link_during_analysis):
                self.run_audit(source, strip=strip)
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(source.samefile(strip))
            with Image.open(strip) as picture:
                self.assertEqual(picture.format, "PNG")
                picture.load()

    def test_strip_save_failure_preserves_existing_output_and_cleans_tempfile(self):
        with tempfile.TemporaryDirectory() as folder:
            strip = Path(folder) / "strip.png"
            Image.new("RGB", (1, 1)).save(strip)
            before = strip.read_bytes()

            def fail_after_partial_write(canvas, output, **kwargs):
                if isinstance(output, Path):
                    output.write_bytes(b"partial PNG")
                else:
                    output.write(b"partial PNG")
                raise OSError("disk full")

            with patch.object(Image.Image, "save", fail_after_partial_write):
                with self.assertRaisesRegex(OSError, "disk full"):
                    write_strip([], strip)
            self.assertEqual(strip.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [strip])

    def test_strip_parent_symlink_changed_during_audit_cannot_modify_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inputs, outputs = root / "inputs", root / "outputs"
            inputs.mkdir()
            outputs.mkdir()
            source = inputs / "video.mp4"
            shutil.copyfile(self.moving, source)
            before = source.read_bytes()
            parent = root / "linked-parent"
            parent.symlink_to(outputs, target_is_directory=True)

            def retarget_during_analysis(frames, candidate, provider):
                parent.unlink()
                parent.symlink_to(inputs, target_is_directory=True)
                return {"status": "disabled"}

            with patch("hookcheck.audit.analyze", side_effect=retarget_during_analysis):
                self.run_audit(source, strip=parent / source.name)
            self.assertEqual(source.read_bytes(), before)
            with Image.open(outputs / source.name) as picture:
                self.assertEqual(picture.format, "PNG")
                picture.load()

    def test_fake_vision_changes_semantic_verdict_and_receives_frames(self):
        seen = []
        def fake(frames, candidate):
            seen.extend(frames)
            return {"action_visible_at_start": True, "mostly_talking_or_posing": False,
                    "description": "A cup is already spilling.", "on_screen_text": [],
                    "candidate_action_visible": None, "candidate_description": None}
        result = self.run_audit(self.static, vision_provider=fake)
        self.assertEqual(result["risk"], "low")
        self.assertEqual([frame.time_s for frame in seen], [0, 0.5, 1, 1.5])
        self.assertTrue(all(frame.image[:2] == b"\xff\xd8" for frame in seen))
        def talking(frames, candidate):
            return {"action_visible_at_start": False, "mostly_talking_or_posing": True,
                    "description": "Someone announces a problem without showing it.", "on_screen_text": [],
                    "candidate_action_visible": False, "candidate_description": "Someone poses."}
        self.assertEqual(self.run_audit(self.moving, vision_provider=talking)["risk"], "high")

    def test_provider_failure_keeps_measured_report(self):
        def broken(frames, candidate):
            raise ValueError("malformed JSON")
        report = self.run_audit(self.static, vision_provider=broken)
        self.assertEqual(report["vision"]["status"], "unavailable")
        self.assertEqual(report["risk"], "high")
        self.assertIsInstance(report["measurements"]["opening_motion"], float)

    def test_cli_json_strip_and_bad_input(self):
        strip = self.root / "strip.png"
        env = dict(os.environ, HOOKCHECK_PROVIDER="none")
        result = subprocess.run([sys.executable, "-m", "hookcheck", str(self.moving),
                                 "--json", "--strip", str(strip)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["risk"], "low")
        self.assertEqual(strip.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        failure = subprocess.run([sys.executable, "-m", "hookcheck", str(self.root / "missing.mp4"), "--json"],
                                 env=env, capture_output=True, text=True)
        self.assertEqual(failure.returncode, 2)
        self.assertIn("error", json.loads(failure.stdout))
        self.assertNotIn("Traceback", failure.stderr)
