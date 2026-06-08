"""
为指定 video_id 生成字幕：subtitle.srt + subtitle.vtt + transcript.txt。

三级策略：
1. 用户提供的 user.srt（同名 .srt 跟随 mp4 一起进 inbox）
2. ffmpeg 提 mp4 内嵌字幕流
3. faster-whisper 本地转写（自动下载模型，CPU 也能跑但慢）
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

import imageio_ffmpeg


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"


def srt_to_segments(srt_text: str) -> List[Tuple[float, float, str]]:
    segments: List[Tuple[float, float, str]] = []
    blocks = re.split(r"\r?\n\r?\n", srt_text.strip())
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        time_line = lines[1] if re.search(r"\d{2}:\d{2}:\d{2}", lines[1]) else (lines[0] if re.search(r"\d{2}:\d{2}:\d{2}", lines[0]) else None)
        if not time_line:
            continue
        m = re.search(r"(\d{2}):(\d{2}):(\d{2}[,.]\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}[,.]\d{3})", time_line)
        if not m:
            continue
        start = _hms_to_s(m.group(1), m.group(2), m.group(3))
        end = _hms_to_s(m.group(4), m.group(5), m.group(6))
        text_lines = lines[(lines.index(time_line) + 1):]
        text = " ".join(text_lines).strip()
        segments.append((start, end, text))
    return segments


def _hms_to_s(h: str, m: str, s_ms: str) -> float:
    s_ms = s_ms.replace(",", ".")
    return int(h) * 3600 + int(m) * 60 + float(s_ms)


def segments_to_srt(segments: List[Tuple[float, float, str]]) -> str:
    out = []
    for i, (start, end, text) in enumerate(segments, 1):
        out.append(str(i))
        out.append(f"{_s_to_hms(start, ',')} --> {_s_to_hms(end, ',')}")
        out.append(text)
        out.append("")
    return "\n".join(out)


def segments_to_vtt(segments: List[Tuple[float, float, str]]) -> str:
    out = ["WEBVTT", ""]
    for start, end, text in segments:
        out.append(f"{_s_to_hms(start, '.')} --> {_s_to_hms(end, '.')}")
        out.append(text)
        out.append("")
    return "\n".join(out)


def segments_to_transcript(segments: List[Tuple[float, float, str]]) -> str:
    lines = []
    for start, _, text in segments:
        mm = int(start // 60)
        ss = int(start % 60)
        lines.append(f"[{mm:02d}:{ss:02d}] {text}")
    return "\n".join(lines)


def _s_to_hms(s: float, sep: str = ",") -> str:
    if s < 0:
        s = 0.0
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", sep)


def try_user_srt(video_dir: Path) -> Optional[List[Tuple[float, float, str]]]:
    user_srt = video_dir / "user.srt"
    if not user_srt.exists():
        return None
    try:
        text = user_srt.read_text(encoding="utf-8", errors="replace")
        return srt_to_segments(text)
    except Exception as e:
        print(f"[warn] user.srt parse failed: {e}", file=sys.stderr)
        return None


def try_embedded_subtitle(video_dir: Path) -> Optional[List[Tuple[float, float, str]]]:
    video_path = video_dir / "video.mp4"
    out_srt = video_dir / "embedded.srt"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-hide_banner", "-y", "-i", str(video_path),
        "-map", "0:s:0", "-c:s", "srt", str(out_srt),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not out_srt.exists() or out_srt.stat().st_size < 30:
        if out_srt.exists():
            out_srt.unlink()
        return None
    try:
        return srt_to_segments(out_srt.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def whisper_transcribe(video_dir: Path, model_size: str = "small") -> List[Tuple[float, float, str]]:
    from faster_whisper import WhisperModel

    video_path = video_dir / "video.mp4"
    print(f"[whisper] loading model '{model_size}' (first run will download ~150MB-1GB)...", file=sys.stderr)
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    print(f"[whisper] transcribing {video_path.name} (this can take a while)...", file=sys.stderr)

    segments_out: List[Tuple[float, float, str]] = []
    segments, info = model.transcribe(
        str(video_path),
        language="zh",
        beam_size=1,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        segments_out.append((seg.start, seg.end, text))
    print(f"[whisper] got {len(segments_out)} segments (detected language={info.language})", file=sys.stderr)
    return segments_out


def write_outputs(video_dir: Path, segments: List[Tuple[float, float, str]], source: str) -> None:
    (video_dir / "subtitle.srt").write_text(segments_to_srt(segments), encoding="utf-8")
    (video_dir / "subtitle.vtt").write_text(segments_to_vtt(segments), encoding="utf-8")
    (video_dir / "transcript.txt").write_text(segments_to_transcript(segments), encoding="utf-8")

    meta_path = video_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {}
    meta["subtitle_source"] = source
    meta["subtitle_segments"] = len(segments)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def process(video_id: str, whisper_model: str = "small", force: bool = False) -> str:
    video_dir = VIDEOS_DIR / video_id
    if not (video_dir / "video.mp4").exists():
        raise FileNotFoundError(f"{video_dir}/video.mp4 does not exist; run ingest_video first")

    if not force and (video_dir / "subtitle.srt").exists() and (video_dir / "transcript.txt").exists():
        print(f"[skip] {video_id}: subtitle already exists", file=sys.stderr)
        return "cached"

    segments = try_user_srt(video_dir)
    if segments:
        write_outputs(video_dir, segments, "user")
        print(f"[subtitle] {video_id}: source=user  segments={len(segments)}")
        return "user"

    segments = try_embedded_subtitle(video_dir)
    if segments:
        write_outputs(video_dir, segments, "embedded")
        print(f"[subtitle] {video_id}: source=embedded  segments={len(segments)}")
        return "embedded"

    segments = whisper_transcribe(video_dir, model_size=whisper_model)
    if not segments:
        raise RuntimeError(f"{video_id}: whisper returned 0 segments")
    write_outputs(video_dir, segments, f"whisper:{whisper_model}")
    print(f"[subtitle] {video_id}: source=whisper:{whisper_model}  segments={len(segments)}")
    return "whisper"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--whisper-model", default="small", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    process(args.video_id, whisper_model=args.whisper_model, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
