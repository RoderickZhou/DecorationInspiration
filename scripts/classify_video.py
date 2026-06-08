"""
对指定 video_id 调用 Minimax，判断是 tutorial / style / other。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minimax_client import MinimaxClient, MinimaxError, MinimaxConfigError
from _schema_validate import SchemaValidationError, load_schema, validate_or_raise


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "video_classification.schema.json"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "video_classify.md"


def process(video_id: str, force: bool = False) -> dict:
    video_dir = VIDEOS_DIR / video_id
    out_path = video_dir / "analysis" / "classification.json"
    if out_path.exists() and not force:
        return json.loads(out_path.read_text(encoding="utf-8"))

    meta = json.loads((video_dir / "meta.json").read_text(encoding="utf-8"))
    transcript = (video_dir / "transcript.txt").read_text(encoding="utf-8")
    transcript_head = transcript[:6000]

    user_payload = json.dumps({
        "title": meta.get("title", ""),
        "duration_seconds": meta.get("duration_s", 0),
        "transcript_preview": transcript_head,
    }, ensure_ascii=False)

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    schema = load_schema(SCHEMA_PATH)

    client = MinimaxClient()
    resp = client.chat_json(prompt, user_payload, max_tokens=1024)
    output = resp.get("output") if isinstance(resp, dict) and "output" in resp else resp
    if not isinstance(output, dict):
        raise MinimaxError(f"unexpected response shape: {str(resp)[:200]}")

    validate_or_raise(output, schema, SCHEMA_PATH)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    meta["classification"] = {
        "type": output["type"],
        "confidence": output["confidence"],
    }
    meta["status"] = "classified"
    (video_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[classify] {video_id}: type={output['type']}  conf={output['confidence']}  reasoning={output['reasoning'][:80]}")
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
