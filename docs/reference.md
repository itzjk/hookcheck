# Reference

## Vision providers

Choose the provider explicitly with `HOOKCHECK_PROVIDER`. Existing API keys alone never enable uploads.

| Provider | Environment | Default model | Frames leave this machine? |
| --- | --- | --- | --- |
| No AI | `HOOKCHECK_PROVIDER=none` (default) | None | No |
| Ollama | `HOOKCHECK_PROVIDER=ollama` | `qwen2.5vl:7b` | No, with a local model/server |
| Anthropic | `HOOKCHECK_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` | Yes, to Anthropic |
| OpenAI | `HOOKCHECK_PROVIDER=openai`, `OPENAI_API_KEY` | `gpt-4.1-mini` | Yes, to OpenAI |

`HOOKCHECK_MODEL` overrides the model. A vision-capable model is required. For Ollama, install the model and start the server using its [setup guide](https://docs.ollama.com/quickstart) and [vision guide](https://docs.ollama.com/capabilities/vision). `OLLAMA_HOST` defaults to `http://127.0.0.1:11434`; only loopback HTTP endpoints are accepted. hookcheck checks `/api/show` before sending images and refuses remote models, aliases to remote models, and models without vision capability. It does not download models. To disable cloud features in the Ollama server itself, follow [Ollama's local-only configuration](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).

The model sees opening samples at **0, 0.5, 1 and 1.5 seconds**, followed by the alternative-start samples when available. It describes the opening, distinguishes visible action from talking/posing, reads visible text and checks whether the candidate actually shows action. A rejected candidate is not recommended. Responses are schema-checked; missing keys, provider errors, timeouts and malformed responses preserve the local measurements and explain that vision is unavailable. There are no automatic paid retries.

Provider payloads are tested with fakes, including a real loopback HTTP server. Live Anthropic, OpenAI and Ollama model inference remains unverified. Model availability and inference quality can change. Cloud requests have a 45-second socket timeout; model startup may exceed it.

## Measurements and risk rules

| Signal | Method | What it does not establish |
| --- | --- | --- |
| Opening visual change | FFmpeg downsamples to 160 x 90 grayscale at 8 fps; mean absolute pixel difference, divided by 255, over 0-1.5 s | Object motion, emotion or narrative meaning |
| Black first frame | At least 98% of pixels in the actual first decoded frame have luma <= 20/255 | Whether a dark scene is intentional |
| Low-detail first frame | First-frame luma standard deviation < 4/255 | Semantic emptiness; a title card can be meaningful |
| First cut | FFmpeg `scdet`, threshold 12, at the source frame rate throughout the video | Flashes and rapid movement can trigger false cuts |
| First sound | FFmpeg `silencedetect`, -35 dB, minimum silence 0.05 s; first audio stream, preserving its offset from video | **Speech onset is not verified.** Music/noise can trigger it; `voice_onset_s` is always `null` |
| On-screen text | Local Tesseract, if present on `PATH`; otherwise optional vision | OCR and model transcriptions can be wrong |
| Alternative start | Highest-activity later 0.5 s window, sampled every 0.125 s; must exceed 0.008 and be at least 1.5x opening activity | A better story beat or a safe sentence boundary |

These are **implementation thresholds**, not research-derived retention benchmarks. The source cut detector operates before frame-rate resampling. The first-frame check uses an independent seek to zero so a single black source frame cannot disappear in motion sampling. Frame labels are seek targets, not certified presentation timestamps, particularly for variable-rate footage. Rotation is handled by FFmpeg's default autorotation; tiny text may be lost in the 512-pixel vision samples.

The risk rule is deliberately inspectable in [audit.py](../src/hookcheck/audit.py): black adds 3 points; low detail adds 2; motion below 0.005 adds 2, below 0.015 adds 1; no detected sound or a sound delay beyond 0.5 s adds 1. An insufficient motion sample adds 1. Zero points means low, one means medium, two or more means high. Vision showing action in frame zero removes 2 points unless the frame is black. Talking/posing without visible action makes risk at least high; other openings without visible action make it at least medium. **Risk is a heuristic, not a calibrated swipe probability.** A still image can be a great hook and camera shake can fool the motion score. Vision descriptions remain inferences.

Processing is bounded to videos with known duration up to 10 minutes. The full video is scanned for the alternative, so runtime grows with resolution, codec and duration. FFmpeg processes have a 120-second timeout. Grayscale samples are held in a temporary file (about 69 MB maximum at the duration limit), rather than keeping full video frames in memory. Files are cleaned up after analysis. No telemetry, accounts, transcripts, automatic edits or uploads beyond the explicitly selected vision provider.

## Report format

JSON includes `schema_version`, `risk`, `risk_basis`, `reasons`, `fixes`, `measurements`, `vision`, `ocr`, `frames`, and measured `elapsed_s`. Missing measurements are `null`. Exit status is `0` for a report, including high risk or unavailable vision, and `2` for invalid input or a processing failure. Processing errors use JSON when `--json` is selected.

The strip includes opening samples plus two alternative-start samples when available. Short clips include only timestamps that exist. The input file cannot be overwritten by the strip.
