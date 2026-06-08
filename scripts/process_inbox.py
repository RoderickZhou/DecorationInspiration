"""
端到端编排：扫 data/videos/inbox/，对每个新视频依次执行:
  ingest -> extract_subtitle -> extract_keyframes -> classify -> {analyze_tutorial | analyze_style}

每步独立幂等，单步失败不影响其他视频。所有产物落到 data/videos/<id>/。
最后聚合所有 captions.json 输出 data/style_index.json，给 demo/style.html 用。
"""
import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingest_video
import extract_subtitle
import extract_keyframes
import classify_video
import analyze_tutorial
import analyze_style


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"


def all_video_ids() -> list:
    ids = []
    for d in VIDEOS_DIR.iterdir() if VIDEOS_DIR.exists() else []:
        if d.is_dir() and d.name != "inbox" and (d / "meta.json").exists():
            ids.append(d.name)
    return sorted(ids)


def process_single(video_id: str, whisper_model: str, force: bool) -> dict:
    meta_path = VIDEOS_DIR / video_id / "meta.json"
    status = {"video_id": video_id, "steps": {}, "errors": []}

    steps = [
        ("subtitle", lambda: extract_subtitle.process(video_id, whisper_model=whisper_model, force=force)),
        ("keyframes", lambda: extract_keyframes.process(video_id, force=force)),
        ("classify", lambda: classify_video.process(video_id, force=force)),
    ]

    for name, fn in steps:
        try:
            fn()
            status["steps"][name] = "ok"
        except Exception as e:
            status["steps"][name] = f"failed: {type(e).__name__}: {e}"
            status["errors"].append(f"{name}: {e}")
            print(f"[error] {video_id}/{name}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    if "classify" in status["steps"] and status["steps"]["classify"] == "ok":
        cls_path = VIDEOS_DIR / video_id / "analysis" / "classification.json"
        try:
            cls = json.loads(cls_path.read_text(encoding="utf-8"))
            vtype = cls.get("type", "other")
        except Exception:
            vtype = "other"

        if vtype == "tutorial":
            try:
                analyze_tutorial.process(video_id, force=force)
                status["steps"]["analyze_tutorial"] = "ok"
            except Exception as e:
                status["steps"]["analyze_tutorial"] = f"failed: {e}"
                print(f"[error] {video_id}/analyze_tutorial: {e}", file=sys.stderr)
        elif vtype == "style":
            try:
                analyze_style.process(video_id, force=force)
                status["steps"]["analyze_style"] = "ok"
            except Exception as e:
                status["steps"]["analyze_style"] = f"failed: {e}"
                print(f"[error] {video_id}/analyze_style: {e}", file=sys.stderr)
        else:
            status["steps"]["analyze_other"] = "skipped (type=other)"

    return status


def rebuild_style_index() -> int:
    """聚合所有 style 类视频的 captions.json -> data/style_index.json。"""
    items = []
    for vid in all_video_ids():
        captions = VIDEOS_DIR / vid / "analysis" / "captions.json"
        if not captions.exists():
            continue
        data = json.loads(captions.read_text(encoding="utf-8"))
        overall = data.get("overall", {})
        for fr in data.get("frames", []):
            items.append({
                "video_id": vid,
                "video_title": data.get("title", vid),
                "ts": fr.get("ts"),
                "frame_path": f"data/videos/{vid}/frames/{fr.get('path')}",
                "caption": fr.get("caption", ""),
                "design_points": fr.get("design_points", []),
                "tags": fr.get("tags") or {"style": [], "space": []},
                "overall_style": overall.get("style_tags", []),
                "overall_space": overall.get("space_tags", []),
            })
    out = PROJECT_ROOT / "data" / "style_index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"frames": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[style_index] {len(items)} frames -> {out}")
    return len(items)


def rebuild_video_index() -> int:
    """聚合所有 video 的 meta.json -> data/video_index.json，给 demo/index.html 用。"""
    items = []
    for vid in all_video_ids():
        meta_path = VIDEOS_DIR / vid / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cls = meta.get("classification") or {}
        first_frame = None
        manifest = VIDEOS_DIR / vid / "frames_manifest.json"
        if manifest.exists():
            frames = json.loads(manifest.read_text(encoding="utf-8"))
            if frames:
                first_frame = f"data/videos/{vid}/frames/{frames[0]['path']}"
        items.append({
            "video_id": vid,
            "title": meta.get("title", vid),
            "duration_s": meta.get("duration_s", 0),
            "type": cls.get("type", "unknown"),
            "confidence": cls.get("confidence", 0),
            "status": meta.get("status", "unknown"),
            "subtitle_source": meta.get("subtitle_source", "?"),
            "keyframes_count": meta.get("keyframes_count", 0),
            "cover": first_frame,
            "ingested_at": meta.get("ingested_at", ""),
        })
    items.sort(key=lambda x: x["ingested_at"], reverse=True)
    out = PROJECT_ROOT / "data" / "video_index.json"
    out.write_text(json.dumps({"videos": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[video_index] {len(items)} videos -> {out}")
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--whisper-model", default="small", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--force", action="store_true", help="force redo all steps")
    parser.add_argument("--only-rebuild-indexes", action="store_true", help="skip processing, only refresh index files")
    parser.add_argument("--video-id", help="process this single id (must already exist in data/videos/)")
    args = parser.parse_args()

    if not args.only_rebuild_indexes:
        print("=== Step A: ingest from inbox ===", file=sys.stderr)
        ingest_video.main()
        print()

        targets = [args.video_id] if args.video_id else all_video_ids()
        print(f"=== Step B: process {len(targets)} videos ===", file=sys.stderr)
        statuses = []
        for vid in targets:
            print(f"\n--- {vid} ---", file=sys.stderr)
            statuses.append(process_single(vid, whisper_model=args.whisper_model, force=args.force))

    print("\n=== Step C: rebuild indexes ===", file=sys.stderr)
    rebuild_video_index()
    rebuild_style_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
