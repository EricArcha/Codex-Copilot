# Project introduction video

Owner: repository introduction media. These files stay outside installed product trees.

The approved direction is parchment editorial motion, English headings with short Chinese copy, 16:9, about 24 seconds, music plus restrained sound effects. The source is a self-contained HTML animation; its export uses the huashu-design seek renderer and FFmpeg. It needs no HyperFrames runtime or CLI.

Open `index.html` directly to preview; use the controls below the canvas to play, seek and enable sound. Recording hides these controls. The central route is a workflow diagram, not a video-player progress bar. The film illustrates product policy rather than replaying a measured development task.

The final web asset, master MP4, GIF and poster are in `exports/`. The browser preview uses `assets/soundtrack.mp3`. Source facts, design constraints and audio provenance are in `product-facts.md`, `brand-spec.md` and `shot-plan.json`.

## Reproduce

Requirements: Python 3.11+, Node.js, FFmpeg/ffprobe, global Playwright with Chromium, and the huashu-design skill. This is optional video tooling, not a Codex-Copilot runtime dependency.

```sh
NODE_PATH=$(npm root -g) node verify.cjs
python3 export-video.py
```

Use `--skill-root /path/to/huashu-design` if the skill is outside the standard `.agents/skills` or `.codex/skills` locations. Export creates a 1080p native 60fps H.264/AAC master, a 720p 30fps web version with faststart, a silent 640px GIF, and a JPEG poster. `embed.html` is a native video-player example for the introduction page.

## Verification — 2026-10-04

Seven representative frames including the first and final frame were inspected. Repeated forward/backward seeks reproduce the same pixels. Play, pause, restart, sound toggle, scrubbing and phone-size fitting pass with zero browser errors. The final H.264/AAC web export loads and plays in Chromium; both MP4s are 24 seconds and carry an audio stream. The soundtrack uses a -18 LUFS normalization target and -1.5 dBTP ceiling.

Repository checks: 118 tests run successfully, with 7 Windows-only tests skipped on macOS; Skill validator, release metadata and whitespace checks pass.
