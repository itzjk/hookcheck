# Motivation and related work

A strong opening line does not guarantee that the viewer can **see** the stakes. YouTube measures [how many viewers chose to view versus swiped away](https://support.google.com/youtube/answer/12942217?co=YOUTUBE._YTVideoType%3Dshorts&hl=en). That makes the first visible beat worth checking separately from the script.

The motivating creator observation, reported in October 2026, was 64% swiped away for a seated talking opening, versus 28-30% for openings that showed the accident from frame zero in the same series. The underlying analytics are not public and were not independently verified here. This is a reason to investigate, **not evidence of causality or a calibration dataset**. The 1.5-second audit window is an editing choice, not a universal platform threshold.

Related work, reviewed October 27, 2026:

- [claude-youtube](https://github.com/AgriciDaniel/claude-youtube) covers hooks, scripts, analytics and creator workflows. hookcheck starts from a local video file and produces a fixed report.
- [DDaverse's hook analyzer](https://github.com/ddaverse/shorts-reels-hook-analyzer) describes script and hook optimization. Its public repository contains a README rather than a comparable local video CLI.
- [claude-video-vision](https://github.com/jordanrendric/claude-video-vision) already extracts real frames and measures video structure. Its README describes a general perception layer for Claude Code, while hookcheck packages a specific opening audit, risk rule, alternative start and scriptable JSON into one command.

Video-frame analysis already exists. The useful distinction here is the focused audit and local-model path, not a claim to have invented it. No comprehensive market survey or “first ever” claim is made.

Technical sources: [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html#scdet), [silence detection](https://ffmpeg.org/ffmpeg-filters.html#silencedetect), [Ollama vision](https://docs.ollama.com/capabilities/vision), [Anthropic vision](https://platform.claude.com/docs/en/build-with-claude/vision), [OpenAI image input](https://developers.openai.com/api/docs/guides/images-vision). Consulted October 27, 2026.

