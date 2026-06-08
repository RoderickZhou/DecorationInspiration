"""
对 style 类视频生成 overall 风格 + 每帧配文。

每帧的"配文"由 Minimax 基于该帧时间戳前后 ±15s 的字幕上下文 + 视频整体语境推断（M2.7 是纯文本模型，
看不到图本身；v0.3 接入 VL 模型后此脚本可只替换调用部分）。
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minimax_client import MinimaxClient, MinimaxError, MinimaxConfigError
from _schema_validate import SchemaValidationError, load_schema, validate_or_raise


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"
SCHEMAS = PROJECT_ROOT / "schemas"
PROMPTS = PROJECT_ROOT / "prompts"


def parse_transcript(transcript: str) -> List[Tuple[float, str]]:
    items: List[Tuple[float, str]] = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            ts_part, text = line.split("]", 1)
            mm, ss = ts_part[1:].split(":")
            ts = int(mm) * 60 + int(ss)
            items.append((float(ts), text.strip()))
        except Exception:
            continue
    return items


def context_around(transcript_items: List[Tuple[float, str]], ts: float, window_s: float = 15.0) -> str:
    chunk: List[str] = []
    for t, text in transcript_items:
        if abs(t - ts) <= window_s:
            chunk.append(text)
    return " ".join(chunk).strip()


def process(video_id: str, force: bool = False) -> dict:
    video_dir = VIDEOS_DIR / video_id
    out_path = video_dir / "analysis" / "style.json"
    if out_path.exists() and not force:
        return json.loads(out_path.read_text(encoding="utf-8"))

    meta = json.loads((video_dir / "meta.json").read_text(encoding="utf-8"))
    title = meta.get("title", "")

    transcript = (video_dir / "transcript.txt").read_text(encoding="utf-8")
    transcript_items = parse_transcript(transcript)

    manifest_path = video_dir / "frames_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"{video_id}: missing frames_manifest.json (run extract_keyframes first)")
    frames = json.loads(manifest_path.read_text(encoding="utf-8"))

    frame_contexts = []
    for fr in frames:
        ctx = context_around(transcript_items, fr["ts"], window_s=15.0)
        frame_contexts.append({
            "ts": fr["ts"],
            "transcript_window": ctx or "(此帧无对应字幕，可能是镜头切换或留白)",
        })

    user_payload = json.dumps({
        "title": title,
        "full_transcript": transcript,
        "frames_with_context": frame_contexts,
    }, ensure_ascii=False)

    prompt = (PROMPTS / "video_style.md").read_text(encoding="utf-8")
    schema = load_schema(SCHEMAS / "video_style.schema.json")

    client = MinimaxClient()
    resp = client.chat_json(prompt, user_payload, max_tokens=8192)
    output = resp.get("output") if isinstance(resp, dict) and "output" in resp else resp
    if not isinstance(output, dict):
        raise MinimaxError(f"unexpected response shape: {str(resp)[:200]}")

    validate_or_raise(output, schema, SCHEMAS / "video_style.schema.json")

    if len(output["frames"]) != len(frames):
        print(f"[warn] frame count mismatch: schema={len(output['frames'])} vs manifest={len(frames)}", file=sys.stderr)

    for fr, fr_output in zip(frames, output["frames"]):
        fr["caption"] = fr_output.get("caption", "")
        fr["design_points"] = fr_output.get("design_points", [])
        fr["tags"] = fr_output.get("tags", {})

    captions_path = video_dir / "analysis" / "captions.json"
    captions_path.parent.mkdir(parents=True, exist_ok=True)
    captions_path.write_text(
        json.dumps({
            "video_id": video_id,
            "title": title,
            "overall": output["overall"],
            "frames": frames,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    meta["status"] = "analyzed_style"
    meta["style_overall"] = output["overall"]
    (video_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[style] {video_id}: headline={output['overall']['headline'][:60]}  frames={len(frames)}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        process(args.video_id, force=args.force)
    except MinimaxConfigError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
