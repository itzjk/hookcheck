import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import unittest
from unittest.mock import patch

from hookcheck.media import Frame
from hookcheck.vision import analyze, inspect, parse, post


OBSERVATION = {"action_visible_at_start": True, "mostly_talking_or_posing": False,
               "description": "Coffee is spilling onto a keyboard.", "on_screen_text": ["Oops"],
               "candidate_action_visible": None, "candidate_description": None}


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.frames = [Frame(stamp, b"image-bytes") for stamp in (0, 0.5, 1, 1.5)]

    def test_provider_payloads_and_response_shapes(self):
        calls = []
        def fake(url, payload, headers, **kwargs):
            calls.append((url, payload, headers, kwargs))
            if url.endswith("/api/show"):
                return {"model_info": {"general.architecture": "qwen25vl"}, "capabilities": ["vision"]}
            if "anthropic" in url:
                return {"content": [{"type": "text", "text": json.dumps(OBSERVATION)}]}
            if "openai" in url:
                return {"output": [{"type": "message", "content": [
                    {"type": "output_text", "text": json.dumps(OBSERVATION)}]}]}
            return {"message": {"content": json.dumps(OBSERVATION)}}
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://127.0.0.1:11434"}):
            for provider in ("ollama", "anthropic", "openai"):
                value = inspect(self.frames, [], provider, "test-model", "test-key", transport=fake)
                self.assertEqual(value, OBSERVATION)
        ollama, anthropic, openai = calls[1:]
        self.assertEqual(len(ollama[1]["messages"][0]["images"]), 4)
        self.assertFalse(ollama[1]["stream"])
        self.assertEqual(anthropic[2]["x-api-key"], "test-key")
        self.assertEqual(openai[2]["Authorization"], "Bearer test-key")
        self.assertEqual(anthropic[1]["messages"][0]["content"][1]["source"]["data"], base64.b64encode(b"image-bytes").decode())
        self.assertEqual(openai[1]["input"][0]["content"][1]["type"], "input_image")

    def test_invalid_schema_is_rejected_instead_of_coercing_false(self):
        for change in ({"action_visible_at_start": "false"}, {"description": ""},
                       {"candidate_action_visible": 1}, {"on_screen_text": "Oops"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse(json.dumps({**OBSERVATION, **change}))
        self.assertEqual(parse("```json\n" + json.dumps(OBSERVATION) + "\n```"), OBSERVATION)

    def test_default_and_missing_key_make_no_network_requests(self):
        with patch.dict(os.environ, {}, clear=True), patch("hookcheck.vision.inspect") as request:
            self.assertEqual(analyze(self.frames, [])["status"], "disabled")
            for provider in ("anthropic", "openai"):
                os.environ["HOOKCHECK_PROVIDER"] = provider
                self.assertEqual(analyze(self.frames, [])["status"], "unavailable")
            request.assert_not_called()

    def test_local_vision_never_posts_images_to_cloud_or_unverified_models(self):
        for host in ("https://ollama.com", "http://example.org:11434", "http://localhost:11434/path"):
            with patch.dict(os.environ, {"OLLAMA_HOST": host}), self.assertRaises(ValueError):
                inspect(self.frames, [], "ollama", "vision-model", transport=lambda *a, **k: self.fail("Network called"))
        calls = []
        def remote(url, payload, headers, **kwargs):
            calls.append(payload)
            return {"remote_host": "https://ollama.com", "model_info": {"architecture": "cloud"}, "capabilities": ["vision"]}
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://127.0.0.1:11434"}), self.assertRaises(ValueError):
            inspect(self.frames, [], "ollama", "innocent-alias", transport=remote)
        self.assertEqual(calls, [{"model": "innocent-alias"}])

    def test_real_local_http_provider_and_http200_error(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, payload))
                if self.path == "/api/show":
                    body = {"model_info": {"architecture": "test"}, "capabilities": ["vision"]}
                elif self.path == "/error":
                    body = {"error": "model unavailable"}
                elif self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/leak")
                    self.end_headers()
                    return
                else:
                    body = {"message": {"content": json.dumps(OBSERVATION)}}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            host = f"http://127.0.0.1:{server.server_port}"
            with patch.dict(os.environ, {"OLLAMA_HOST": host, "HOOKCHECK_PROVIDER": "ollama", "HOOKCHECK_MODEL": "fake-local"}):
                result = analyze(self.frames, [])
            self.assertEqual(result["status"], "inferred")
            self.assertEqual(result["observation"], OBSERVATION)
            self.assertEqual([path for path, _ in requests], ["/api/show", "/api/chat"])
            with self.assertRaisesRegex(ValueError, "error response"):
                post(host + "/error", {}, {}, local=True)
            with self.assertRaisesRegex(ValueError, "redirects"):
                post(host + "/redirect", {}, {}, local=True)
            self.assertNotIn("/leak", [path for path, _ in requests])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
