"""
为指定 video_id 抽取关键帧。

策略：
- ffmpeg 场景检测（select 'gt(scene,threshold)'）抽场景切换帧
- 如果场景检测结果太少（短视频或镜头平稳），用固定间隔补足
- 落到 data/videos/<id>/frames/keyframe_<index>_<ts>.jpg
- 每张图 800px 宽（保留比例），webp 是不是太省，先用 jpg 保兼容
- 输出 frames_manifest.json 记录每帧的时间戳，供 analyze_style 使用
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

import imageio_ffmpeg


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"


def run_ffmpeg_scene(video_path: Path, out_dir: Path, threshold: float, max_frames: int, target_width: int) -> List[Dict[str, Any]]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_pattern = str(out_dir / "scene_%04d.jpg")
    vf = (
        f"select='gt(scene,{threshold})',"
        f"scale={target_width}:-2,"
        f"setpts=N/(FRAME_RATE*TB)"
    )
    cmd = [
        ffmpeg, "-hide_banner", "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-vsync", "vfr",
        "-frames:v", str(max_frames * 2),
        "-q:v", "3",
        out_pattern,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"[ffmpeg-scene] returncode={proc.returncode}", file=sys.stderr)
        print(proc.stderr[-800:], file=sys.stderr)

    return _collect_with_pts(video_path, sorted(out_dir.glob("scene_*.jpg")), threshold, target_width)


def run_ffmpeg_interval(video_path: Path, out_dir: Path, count: int, target_width: int, duration_s: float) -> List[Dict[str, Any]]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if count <= 0 or duration_s <= 0:
        return []
    step = max(2.0, duration_s / (count + 1))
    fps = 1.0 / step
    out_pattern = str(out_dir / "interval_%04d.jpg")
    vf = f"fps={fps},scale={target_width}:-2"
    cmd = [
        ffmpeg, "-hide_banner", "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-vsync", "vfr",
        "-frames:v", str(count),
        "-q:v", "3",
        out_pattern,
    ]
    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    frames = sorted(out_dir.glob("interval_*.jpg"))
    items: List[Dict[str, Any]] = []
    for i, p in enumerate(frames):
        ts = round(step * (i + 1), 2)
        items.append({"path": p.name, "ts": ts, "source": "interval"})
    return items


def _collect_with_pts(video_path: Path, frame_paths: List[Path], threshold: float, target_width: int) -> List[Dict[str, Any]]:
    """ffmpeg scene 选帧不直接给时间戳。这里用 ffprobe-style 二次扫描拿到 pts。"""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    vf = f"select='gt(scene,{threshold})',showinfo"
    cmd = [
        ffmpeg, "-hide_banner",
        "-i", str(video_path),
        "-vf", vf,
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    pts_list: List[float] = []
    for m in re.finditer(r"pts_time:([\d.]+)", proc.stderr or ""):
        pts_list.append(float(m.group(1)))

    items: List[Dict[str, Any]] = []
    for i, p in enumerate(frame_paths):
        ts = pts_list[i] if i < len(pts_list) else 0.0
        items.append({"path": p.name, "ts": round(ts, 2), "source": "scene"})
    return items


def renumber_and_rename(frames_dir: Path, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items_sorted = sorted(items, key=lambda x: x["ts"])
    renamed: List[Dict[str, Any]] = []
    for i, it in enumerate(items_sorted, 1):
        old = frames_dir / it["path"]
        if not old.exists():
            continue
        new_name = f"keyframe_{i:03d}_{int(it['ts']):05d}.jpg"
        new_path = frames_dir / new_name
        if old.resolve() != new_path.resolve():
            old.rename(new_path)
        renamed.append({"index": i, "ts": it["ts"], "path": new_name, "source": it["source"]})
    return renamed


def process(video_id: str, max_frames: int = 24, threshold: float = 0.35, target_width: int = 960, force: bool = False) -> List[Dict[str, Any]]:
    video_dir = VIDEOS_DIR / video_id
    video_path = video_dir / "video.mp4"
    if not video_path.exists():
        raise FileNotFoundError(str(video_path))

    frames_dir = video_dir / "frames"
    manifest_path = video_dir / "frames_manifest.json"

    if manifest_path.exists() and not force:
        print(f"[skip] {video_id}: frames already extracted", file=sys.stderr)
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    if frames_dir.exists():
        for f in frames_dir.glob("*.jpg"):
            f.unlink()
    frames_dir.mkdir(parents=True, exist_ok=True)

    meta_path = video_dir / "meta.json"
    duration_s = 0.0
    if meta_path.exists():
        try:
            duration_s = float(json.loads(meta_path.read_text(encoding="utf-8")).get("duration_s") or 0)
        except Exception:
            duration_s = 0.0

    scene_items = run_ffmpeg_scene(video_path, frames_dir, threshold, max_frames, target_width)
    print(f"[keyframes] {video_id}: scene-detected {len(scene_items)} frames")

    if len(scene_items) < max(6, max_frames // 3):
        need = max(6, max_frames // 2) - len(scene_items)
        interval_items = run_ffmpeg_interval(video_path, frames_dir, need, target_width, duration_s)
        print(f"[keyframes] {video_id}: + interval-sampled {len(interval_items)} frames")
        scene_items.extend(interval_items)

    # 若过多，按时间戳均匀截断
    if len(scene_items) > max_frames:
        step = len(scene_items) / max_frames
        keep_idx = {int(step * i) for i in range(max_frames)}
        scene_items = [it for i, it in enumerate(sorted(scene_items, key=lambda x: x["ts"])) if i in keep_idx]
        print(f"[keyframes] {video_id}: trimmed to {len(scene_items)}", file=sys.stderr)

    manifest = renumber_and_rename(frames_dir, scene_items)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["keyframes_count"] = len(manifest)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[keyframes] {video_id}: kept {len(manifest)} frames")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--max-frames", type=int, default=24)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    process(args.video_id, max_frames=args.max_frames, threshold=args.threshold, target_width=args.width, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
