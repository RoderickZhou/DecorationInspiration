"""
扫 data/videos/inbox/ 下的视频文件（mp4/mkv/webm/mov），规范化命名 + 移入 data/videos/<id>/，写 meta.json。

非 mp4 容器走 ffmpeg -c copy remux 到 mp4（B 站源 H.264+AAC 秒级完成），保证下游浏览器嵌入播放兼容。
幂等：已存在 data/videos/<id>/meta.json 的会跳过。
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import imageio_ffmpeg


TZ_CN = timezone(timedelta(hours=8))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = PROJECT_ROOT / "data" / "videos" / "inbox"
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"
SUPPORTED_EXTS = {".mp4", ".mkv", ".webm", ".mov"}


def now_iso() -> str:
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


def slugify(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", "_", name)
    name = name.strip("._")
    return name or "untitled"


def remux_to_mp4(src: Path, dst: Path) -> str:
    """把任意容器流复制为 mp4。返回 "copy" / "transcode" 标识使用的策略。

    优先 -c copy（秒级 remux）；失败则 fallback transcode（H.264 + AAC）。
    成功后删除源文件，模拟 shutil.move 语义。
    """
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    dst.parent.mkdir(parents=True, exist_ok=True)

    copy_cmd = [
        ffmpeg_bin, "-hide_banner", "-loglevel", "warning", "-y",
        "-i", str(src),
        "-c", "copy",
        "-movflags", "+faststart",
        str(dst),
    ]
    proc = subprocess.run(copy_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
        src.unlink()
        return "copy"

    print(f"[remux] -c copy failed for {src.name}, falling back to transcode. stderr tail: {(proc.stderr or '')[-400:]}", file=sys.stderr)
    if dst.exists():
        dst.unlink()

    transcode_cmd = [
        ffmpeg_bin, "-hide_banner", "-loglevel", "warning", "-y",
        "-i", str(src),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(dst),
    ]
    proc2 = subprocess.run(transcode_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc2.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg transcode failed: {(proc2.stderr or '')[-400:]}")
    src.unlink()
    return "transcode"


def ffprobe_info(video_path: Path) -> Dict[str, Any]:
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    if not Path(ffprobe_bin).exists():
        ffprobe_bin = ffmpeg_bin

    cmd = [
        ffmpeg_bin, "-hide_banner", "-i", str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    stderr = proc.stderr or ""

    duration_match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", stderr)
    duration_s = 0.0
    if duration_match:
        h, m, s = duration_match.groups()
        duration_s = int(h) * 3600 + int(m) * 60 + float(s)

    video_codec = ""
    width = height = 0
    codec_match = re.search(r"Stream #\d+:\d+[^:]*:\s*Video:\s*(\w+)", stderr)
    if codec_match:
        video_codec = codec_match.group(1)
    # 分辨率单独抓：旧正则会被两点冲掉——流标签 [0x1] 让 (und) 可选组失配，
    # 像素格式 (tv, bt709, progressive) 里的逗号又冲掉按逗号分段的逻辑。直接在 Video 行找 WxH。
    res_match = re.search(r"Video:.*?\b(\d{2,5})x(\d{2,5})\b", stderr)
    if res_match:
        width = int(res_match.group(1))
        height = int(res_match.group(2))

    has_subtitle = bool(re.search(r"Stream #\d+:\d+(?:\([^\)]+\))?:\s*Subtitle:", stderr))

    return {
        "duration_s": round(duration_s, 2),
        "video_codec": video_codec,
        "width": width,
        "height": height,
        "has_embedded_subtitle": has_subtitle,
    }


def ingest_one(src_path: Path) -> Optional[str]:
    base = src_path.stem
    video_id = slugify(base)
    target_dir = VIDEOS_DIR / video_id

    meta_path = target_dir / "meta.json"
    if meta_path.exists():
        print(f"[skip] {video_id}: already ingested", file=sys.stderr)
        return None

    target_dir.mkdir(parents=True, exist_ok=True)

    target_video = target_dir / "video.mp4"
    sidecar_srt = src_path.with_suffix(".srt")  # 取扩展名前的兄弟 .srt

    src_ext = src_path.suffix.lower()
    if src_ext == ".mp4":
        shutil.move(str(src_path), str(target_video))
        remux_strategy = "none"
    else:
        remux_strategy = remux_to_mp4(src_path, target_video)
        print(f"[remux] {src_path.name} -> video.mp4 ({remux_strategy})", file=sys.stderr)

    user_srt_target = target_dir / "user.srt"
    if sidecar_srt.exists():
        shutil.move(str(sidecar_srt), str(user_srt_target))

    info = ffprobe_info(target_video)

    meta = {
        "video_id": video_id,
        "title": base,
        "original_filename": src_path.name,
        "source": "inbox",
        "remux_strategy": remux_strategy,
        "ingested_at": now_iso(),
        "duration_s": info["duration_s"],
        "video_codec": info["video_codec"],
        "width": info["width"],
        "height": info["height"],
        "has_embedded_subtitle": info["has_embedded_subtitle"],
        "has_user_srt": user_srt_target.exists(),
        "status": "ingested",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ingest] {video_id}  duration={info['duration_s']:.1f}s  codec={info['video_codec']}  user_srt={meta['has_user_srt']}")
    return video_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", default=str(INBOX_DIR))
    args = parser.parse_args()

    inbox = Path(args.inbox)
    inbox.mkdir(parents=True, exist_ok=True)

    video_files = sorted(
        p for p in inbox.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )
    if not video_files:
        print(f"[ingest] no video files in {inbox} (supported: {sorted(SUPPORTED_EXTS)})", file=sys.stderr)
        return 0

    ingested = []
    for video in video_files:
        try:
            vid = ingest_one(video)
            if vid:
                ingested.append(vid)
        except Exception as e:
            print(f"[error] {video.name}: {e}", file=sys.stderr)

    print(f"\ningested: {len(ingested)} videos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
