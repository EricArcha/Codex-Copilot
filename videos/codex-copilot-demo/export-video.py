"""Owner: introduction media. Reproduce exports with huashu-design, Node and FFmpeg."""
from pathlib import Path
import argparse
import json
import os
import subprocess


ROOT = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-capture", action="store_true")
    parser.add_argument("--skill-root", type=Path)
    args = parser.parse_args()
    exports = ROOT / "exports"
    exports.mkdir(exist_ok=True)
    silent = ROOT / "index.mp4"
    if not args.skip_capture:
        candidates = [args.skill_root] if args.skill_root else [
            Path.home() / ".agents/skills/huashu-design",
            Path.home() / ".codex/skills/huashu-design",
        ]
        skill = next((p for p in candidates if (p / "scripts/render-video-seek.js").is_file()), None)
        if skill is None:
            parser.error("huashu-design seek renderer missing; pass --skill-root")
        env = os.environ.copy()
        env["NODE_PATH"] = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
        subprocess.run([
            "node", str(skill / "scripts/render-video-seek.js"), "index.html",
            "--duration=24", "--fps=60", "--width=1920", "--height=1080",
            "--concurrency=4", "--settle=1",
        ], check=True, cwd=ROOT, env=env)
    if not silent.is_file():
        parser.error("Missing captured index.mp4")
    ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    mix = (
        "[0:a]atrim=0:24,lowpass=f=4000,volume=0.30,"
        "afade=t=in:st=0:d=0.3,afade=t=out:st=22.5:d=1.5[bed];"
        "[1:a]highpass=f=800,volume=0.8,asplit=2[c1][c2];"
        "[c1]adelay=4000|4000[a1];[c2]adelay=8500|8500[a2];"
        "[2:a]highpass=f=800,volume=0.75,adelay=13000|13000[a3];"
        "[3:a]highpass=f=800,volume=0.7,adelay=18000|18000[a4];"
        "[bed][a1][a2][a3][a4]amix=inputs=5:duration=first:normalize=0,"
        "alimiter=limit=0.95,loudnorm=I=-18:TP=-1.5:LRA=7[out]"
    )
    run(*ffmpeg, "-i", "assets/music.mp3", "-i", "assets/click.mp3",
        "-i", "assets/snap.mp3", "-i", "assets/complete.mp3", "-filter_complex", mix,
        "-map", "[out]", "-t", "24", "-c:a", "libmp3lame", "-q:a", "2", "assets/soundtrack.mp3")
    master = exports / "codex-copilot-intro-master.mp4"
    web = exports / "codex-copilot-intro-web.mp4"
    gif = exports / "codex-copilot-intro.gif"
    run(*ffmpeg, "-i", silent, "-i", "assets/soundtrack.mp3", "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", "24", "-movflags", "+faststart", master)
    run(*ffmpeg, "-i", master, "-vf", "scale=1280:720,fps=30", "-c:v", "libx264",
        "-crf", "23", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", web)
    run(*ffmpeg, "-i", master, "-filter_complex",
        "fps=12,scale=640:360:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
        "-loop", "0", gif)
    run(*ffmpeg, "-ss", "21", "-i", master, "-frames:v", "1", "-q:v", "2", exports / "poster.jpg")
    for video in (master, web):
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video),
        ]))
        streams = probe["streams"]
        if abs(float(probe["format"]["duration"]) - 24) > .1:
            raise RuntimeError("Unexpected output duration")
        if not any(s["codec_type"] == "audio" for s in streams):
            raise RuntimeError("Missing audio stream")
        print(video.name, video.stat().st_size, "bytes", probe["format"]["duration"], "seconds")
    silent.unlink()  # Remove only the known intermediate created by the seek renderer.


if __name__ == "__main__":
    main()
