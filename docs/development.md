# Development and demo recording

From a clone, create an isolated Python environment and install the package:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

FFmpeg and ffprobe must be on `PATH`. The test fixtures need FFmpeg's `libx264` encoder.

```sh
python -m unittest discover -s tests -v
```

Tests generate MP4s with stationary and moving footage, delayed action, a single black first frame, silence, delayed audio and stream offsets. They assert risk direction, candidate timestamps, cut and onset times, JPEG inputs to fake vision, JSON/PNG CLI output and graceful failure. HTTP tests cover provider payloads, loopback transport, cloud rejection, redirects and HTTP 200 error bodies. Inverting the high/low verdict must fail the static/moving regression test.

CI runs the suite on push and pull request with Python 3.9 and 3.13. A separate Python 3.9 job checks editable installation with pip 21.2.4. Metadata lives in `pyproject.toml`; `setup.py` supports older editable installers. The build requirement stays below setuptools 80 because its legacy develop command delegates to pip inside an isolated build environment.

## Reproduce the examples

```sh
python examples/generate.py
HOOKCHECK_PROVIDER=none hookcheck examples/delayed-action.mp4 --strip examples/delayed-action.png > examples/delayed-action.txt
HOOKCHECK_PROVIDER=none hookcheck examples/action-first.mp4 --strip examples/action-first.png > examples/action-first.txt
```

The videos are synthetic illustrations with a test tone. They test processing and verdict direction, not audience behavior. FFmpeg and Pillow versions can slightly change pixel values or text rendering. Optional Tesseract changes the OCR portion of the reports.

## Record the terminal demo

Install [VHS](https://github.com/charmbracelet/vhs#installation) and its `ttyd` dependency. With `hookcheck` on `PATH`, run from the repository root:

```sh
vhs docs/demo.tape
```

The tape runs both audits with vision disabled and records their complete terminal output. It waits for each command to finish before holding the result on screen. No reports are replayed or fabricated. The target recording lasts 10–25 seconds; check the generated GIF's duration after recording on a slower machine.

For an isolated CLI run without installing through pipx:

```sh
uvx --from git+https://github.com/itzjk/hookcheck hookcheck examples/action-first.mp4
```

See [verification](../VERIFICATION.md) for the checks performed on this revision.
