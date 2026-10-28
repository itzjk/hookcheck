# Verification

Checked October 27, 2026 with Python 3.9.6, FFmpeg 9.0.2 and Pillow 11.3.0. This revision changes documentation and demo assets; the package code, tests, metadata and workflows are unchanged.

## Clean installation and README commands

An isolated pipx installation fetched `git+https://github.com/itzjk/hookcheck` at commit `9027e1ab1c2ce47ba476637f942b2fd8f7d0aa19`. Commands ran from a new temporary directory, with the delayed-action fixture copied there as `video.mp4`.

| Command | Observed result |
| --- | --- |
| `pipx install git+https://github.com/itzjk/hookcheck` | Exit 0; installed version 0.1.0 |
| `hookcheck video.mp4` | Exit 0; HIGH risk, first cut and alternative at 3.000s |
| `hookcheck video.mp4 --json` | Exit 0; valid JSON, high risk, provider none |
| `hookcheck video.mp4 --strip opening.png` | Exit 0; PNG strip created |
| `hookcheck video.mp4 --json --strip opening.png > report.json` | Exit 0; JSON and PNG created |
| `hookcheck --help` | Exit 0; options displayed |
| `hookcheck --version` | Exit 0; hookcheck 0.1.0 |

A separate reviewer repeated the installation and commands using only the README and development instructions. JSON parsing and PNG decoding passed. The reviewer found a stale pipx documentation link; the README now links to the working installation guide.

## Source installation and regression checks

A fresh source copy excluded Git state, existing environments and generated Python caches. The documented `python3 -m venv .venv`, activation, and `python -m pip install -e .` succeeded with pip 21.2.4.

- `python -m unittest discover -s tests -v`: 15 tests passed, measured 4.196 seconds.
- Independent reviewer: 15 tests passed, measured 4.466 seconds.
- `python examples/generate.py`: exit 0. Both regenerated full reports matched the supplied reports exactly.
- Both example MP4s decoded completely with `ffmpeg -v error -xerror -i <clip> -f null -`, exit 0.
- `uvx --from git+https://github.com/itzjk/hookcheck hookcheck examples/action-first.mp4`: exit 0 from the clean source copy with isolated uv directories; LOW risk.

The verdict was temporarily inverted in the disposable source copy. `test_real_video_static_vs_motion_verdict` failed with `AssertionError: 'low' != 'high'`. Restoring the source made the same test pass. Package source in the working repository was never modified.

## Terminal recording

`docs/demo.tape` runs both example audits with vision disabled. The resulting `docs/demo.gif` contains 387 decoded frames at 1200 × 720 pixels, lasts a measured 15.48 seconds and is 257,121 bytes. Both terminal reports were visually inspected, including the final LOW verdict. `ffmpeg -v error -xerror -i docs/demo.gif -f null -` decoded the entire GIF with exit 0. The delayed report shows HIGH risk and a 3.000s alternative; the action-first report shows LOW risk.

The installed VHS 0.12.1 could not launch desktop Chrome inside the execution sandbox: macOS application registration aborted the process. Recording used a temporary build of the same VHS release with its browser launcher pointed at Chrome Headless Shell 156.0.8078.73 in single-process mode. This environment adaptation lives outside the repository; it does not alter the tape, CLI, reports or frame capture. On a normal desktop, the documented command remains `vhs docs/demo.tape`. Regeneration with the unmodified VHS binary inside this sandbox remains blocked.

README length: 677 whitespace-delimited words. Relative documentation links resolve, and the public-file scan found no private paths, credentials or internal project references.

The independent reviewer also decoded all 387 GIF frames and inspected separately extracted HIGH and LOW reports. Both were complete and legible, with no blocking findings.

## CI

The existing [tests workflow run](https://github.com/itzjk/hookcheck/actions/runs/40614002786) completed successfully, verified through GitHub's API on October 27, 2026. It covers Python 3.9 and 3.13 plus legacy editable installation. This documentation revision has not been pushed.

## Coverage limits

Vision adapters use fake responses and a real loopback HTTP server in tests. Live Anthropic, OpenAI and Ollama inference remains unverified. Tesseract was unavailable, so live OCR quality remains unverified. The synthetic examples verify processing and risk direction; they do not establish audience outcomes or speech onset.
