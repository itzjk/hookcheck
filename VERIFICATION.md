# Verification

Checked October 27, 2026 with Python 3.9.6, FFmpeg 9.0.2 and Pillow 11.3.0.

## Executed

A separate source snapshot was committed into a temporary repository, then cloned into a clean directory. Every shell block in the README was executed there with isolated pipx and uv locations.

- `pipx install .`: exit 0.
- `uvx --from . hookcheck examples/action-first.mp4`: exit 0.
- `python -m pip install .`: exit 0 in a fresh virtual environment.
- `python -m unittest discover -s tests -v`: 15 tests passed, measured 4.054 seconds.
- All 8 README shell blocks: exit 0, including JSON, strip generation and example regeneration.
- JSON output parsed successfully; the delayed example proposed `3.000s`.
- Regenerated plain-text demo reports matched the supplied reports exactly.
- Both example MP4s: full video and audio decode with FFmpeg and `-xerror`, exit 0.
- Comparison GIF: all 48 frames decoded successfully.
- Both PNG strips were visually inspected.

The verdict rule was temporarily mutated to swap high and low. `test_real_video_static_vs_motion_verdict` failed with `AssertionError: 'low' != 'high'`. The rule was restored before the clean installation checks.

## Coverage limits

Vision adapters were checked using fake responses and an actual loopback HTTP server. Live OpenAI, Anthropic and Ollama model inference was not exercised. Tesseract was unavailable, so real OCR quality is unverified. Hosted GitHub Actions has not run; the workflow is supplied for pushes and pull requests.

The examples are synthetic illustrations with a test tone. They verify processing and risk direction, not audience behavior. There is no calibration against a public retention dataset. Sound onset does not verify speech onset.
