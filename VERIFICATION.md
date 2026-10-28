# Verification

## Strip alias fix, October 27, 2026

Reproduced the reported failure using a disposable copy of `examples/action-first.mp4`: a hard-linked `strip.png` made the original CLI return exit 0, print LOW risk, leave stderr empty, and change `video.mp4` into a PNG. No example asset was modified.

The old guard compared resolved path names, which cannot identify hard links. The guard now also compares file identity before decoding or calling vision. The resolved output path is retained so retargeting a parent-directory symbolic link during analysis cannot redirect the strip to the video. Strips are saved to a temporary file in the output directory and then atomically replace the destination, protecting the input even if the destination becomes a hard link during analysis. Failed PNG saves preserve the previous output and remove the temporary file.

Before the fix, the new regressions produced six assertion failures: four hard-link rejection subtests, a link created during analysis, and a partial-write failure. The independent review then found the parent-directory symlink case; its regression also failed before normalizing the output path. After the complete fix, `.venv/bin/python -m unittest discover -s tests -v` passed all 19 tests in a measured 4.280 seconds. Same-path, symbolic-link, hard-link and symbolic-link-to-hard-link cases run in both text and JSON modes, assert byte preservation and require exit code 2 with the overwrite error.

The reported hard-link reproduction now exits 2, leaves stdout empty and writes `hookcheck: The strip output must not overwrite the input video.` to stderr. The video remains an MP4 with unchanged SHA-256 `16ce4d2470bb4229282298b4d01f9d5015ee9a73840d5c0d7311c16883b04aa8`.

Both example reports and decoded strip pixels match the committed demo exactly. Both example MP4s fully decode with FFmpeg, exit 0. README length is 713 whitespace-delimited words. The public-file scan found no private paths, personal names, keys or internal project references.

A separate reviewer installed a fresh source copy using only the README and `docs/development.md`, with Python 3.9.6, pip 21.2.4, Pillow 11.3.0 and FFmpeg 9.0.2. `python -m unittest discover -s tests -v` passed 19 tests in a measured 7.977 seconds. All six Usage commands passed from a clean working directory: text, JSON, strip, JSON with strip redirected to a report, help and version. Action-first remained LOW; delayed-action remained HIGH with a 3.000s candidate.

The independent matrix checked eight static aliases in text/JSON modes and six cases that changed a terminal symbolic link, hard link or parent-directory symbolic link during analysis. All preserved the video's bytes and hash; successful strip writes decoded as PNGs. No findings remain in the reviewed scope.

`pipx install git+https://github.com/itzjk/hookcheck` was also rerun with isolated pipx directories and returned exit 0; `hookcheck --version` printed `hookcheck 0.1.0`. That command checks the published revision. The fix was tested through the clean source installation and has not been pushed or run in remote CI. Live vision providers and OCR quality remain unverified.

The remaining sections record checks of the preceding revision.

## Previous revision

Checked October 27, 2026 with Python 3.9.6, FFmpeg 9.0.2 and Pillow 11.3.0. That revision changed documentation and demo assets; the package code, tests, metadata and workflows were unchanged.

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
