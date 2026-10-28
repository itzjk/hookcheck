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

## Legacy editable installation regression

Rechecked October 27, 2026 from a committed source snapshot cloned into a fresh directory, using Python 3.9.6 and pip 21.2.4 without upgrading pip.

- Before the fix, `python -m pip install -e .` exited 1 because pip 21.2.4 could not install an editable pyproject-only checkout.
- Adding `setup.py` alone still failed: setuptools 80's develop command delegated to pip inside the isolated build environment, where pip was unavailable. The build requirement is now `setuptools>=64,<80`; metadata remains in `pyproject.toml`.
- `python -m pip install -e .`: exit 0 in a fresh virtual environment with pip 21.2.4. The installed command returned `hookcheck 0.1.0`.
- `python -m unittest discover -s tests -v`: 15 tests passed after the legacy editable installation, measured 4.859 seconds.
- The same editable installation succeeded with pip 26.0.1 using modern editable wheels; all 15 tests passed, measured 5.192 seconds.
- All 8 README shell blocks: exit 0, including `pipx install .`, `uvx --from . hookcheck examples/action-first.mp4`, normal pip installation, tests, JSON/PNG output and demo regeneration. Tool data and caches were isolated in temporary directories.
- The normal pip installation's test run passed all 15 tests, measured 4.119 seconds. Regenerated reports matched the supplied reports exactly. Both example MP4s decoded fully with FFmpeg and `-xerror`, exit 0.
- Inverting the verdict in the temporary clone made the static/moving regression test fail with `AssertionError: 'low' != 'high'`. After restoring the rule, all 15 tests passed, measured 3.132 seconds.

CI now includes a dedicated Python 3.9 / pip 21.2.4 editable-install job that runs the installed CLI and the full test suite. Hosted execution remains unverified until the workflow runs.

## Coverage limits

Vision adapters were checked using fake responses and an actual loopback HTTP server. Live OpenAI, Anthropic and Ollama model inference was not exercised. Tesseract was unavailable, so real OCR quality is unverified. Hosted GitHub Actions has not run; the workflow is supplied for pushes and pull requests.

The examples are synthetic illustrations with a test tone. They verify processing and risk direction, not audience behavior. There is no calibration against a public retention dataset. Sound onset does not verify speech onset.
