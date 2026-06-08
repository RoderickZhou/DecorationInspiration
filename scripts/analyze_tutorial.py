"""
对 tutorial 类视频生成 outline + notes + quiz，3 次 Minimax 调用。
失败的产物会以 warning 标注但不阻断后续步骤。
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minimax_client import MinimaxClient, MinimaxError, MinimaxConfigError, MinimaxJSONError
from _schema_validate import SchemaValidationError, load_schema, validate_or_raise


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"
SCHEMAS = PROJECT_ROOT / "schemas"
PROMPTS = PROJECT_ROOT / "prompts"


def _save(video_dir: Path, name: str, payload: Any) -> Path:
    p = video_dir / "analysis" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        p.write_text(str(payload), encoding="utf-8")
    return p


def _sanitize_chapter_ts(chapters: list, duration: float) -> None:
    """就地修正章节时间戳：保证单调不减且落在 [0, duration] 内。
    模型在长视频上常把时间戳压缩到开头或给出乱序，这里至少避免点击章节往回跳/越界。
    （真正的"压缩到开头"问题靠 prompt 修；这里是 UI 安全网。）"""
    prev = 0.0
    for ch in chapters:
        try:
            ts = float(ch.get("ts", prev))
        except (TypeError, ValueError):
            ts = prev
        if ts < prev:
            ts = prev
        if duration and ts > duration:
            ts = max(prev, duration - 1)
        ch["ts"] = round(ts, 1)
        prev = ts


def _call_minimax_json(client: MinimaxClient, prompt: str, user_payload: str, schema_path: Path, max_tokens: int) -> Dict[str, Any]:
    resp = client.chat_json(prompt, user_payload, max_tokens=max_tokens)
    output = resp.get("output") if isinstance(resp, dict) and "output" in resp else resp
    if not isinstance(output, dict):
        raise MinimaxError(f"unexpected response shape: {str(resp)[:200]}")
    schema = load_schema(schema_path)
    validate_or_raise(output, schema, schema_path)
    return output


def _call_minimax_json_with_retry(
    client: MinimaxClient,
    prompt: str,
    user_payload: str,
    schema_path: Path,
    max_tokens: int,
    *,
    raw_dump_path: Optional[Path] = None,
    retries: int = 1,
) -> Dict[str, Any]:
    """JSON 解析/schema 失败时把 raw content 落盘以便诊断，再 retry。"""
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return _call_minimax_json(client, prompt, user_payload, schema_path, max_tokens=max_tokens)
        except MinimaxJSONError as e:
            if raw_dump_path is not None:
                try:
                    raw_dump_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_dump_path.write_text(e.raw_content or "", encoding="utf-8")
                except Exception:
                    pass
            last_err = e
            print(f"[retry] JSON 解析失败 (attempt {attempt + 1}/{retries + 1}): {e}", file=sys.stderr)
        except SchemaValidationError as e:
            last_err = e
            print(f"[retry] schema 不通过 (attempt {attempt + 1}/{retries + 1}): {e}", file=sys.stderr)
    assert last_err is not None
    raise last_err


def _call_minimax_text(client: MinimaxClient, prompt: str, user_payload: str, max_tokens: int) -> str:
    """Notes 返回 markdown 而非 JSON；用 chat_json 但要求模型包到 {"markdown": "..."} 里。"""
    wrapper = prompt + "\n\n额外约束：把整段 Markdown **作为字符串放进 `markdown` 字段**，输出 JSON：{\"markdown\": \"...\"}。"
    resp = client.chat_json(wrapper, user_payload, max_tokens=max_tokens)
    md = resp.get("markdown") if isinstance(resp, dict) else None
    if not isinstance(md, str) or not md.strip():
        raise MinimaxError("notes: missing 'markdown' field in response")
    return md


def process(video_id: str, force: bool = False, only: Optional[str] = None) -> Dict[str, Optional[str]]:
    """only ∈ {None, 'outline', 'notes', 'quiz'}：只重跑指定步骤，其余复用磁盘缓存。"""
    video_dir = VIDEOS_DIR / video_id
    transcript = (video_dir / "transcript.txt").read_text(encoding="utf-8")
    if not transcript.strip():
        raise RuntimeError(f"{video_id}: empty transcript")

    meta = json.loads((video_dir / "meta.json").read_text(encoding="utf-8"))
    title = meta.get("title", "")
    duration = meta.get("duration_s", 0)

    user_payload_base = json.dumps({
        "title": title,
        "duration_seconds": duration,
        "transcript_with_ts": transcript,
    }, ensure_ascii=False)

    client = MinimaxClient()
    results: Dict[str, Optional[str]] = {"outline": None, "notes": None, "quiz": None}

    def should_regen(step: str) -> bool:
        """True 表示该步骤要重新调 Minimax。"""
        if only is not None:
            return only == step
        return force

    # 1) outline
    outline_path = video_dir / "analysis" / "outline.json"
    if not should_regen("outline") and outline_path.exists():
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        print(f"[outline] {video_id}: cached")
    elif not should_regen("outline") and only is not None:
        outline = None
        print(f"[outline] {video_id}: no cache & skipped (only={only})", file=sys.stderr)
    else:
        try:
            outline = _call_minimax_json(
                client,
                (PROMPTS / "video_outline.md").read_text(encoding="utf-8"),
                user_payload_base,
                SCHEMAS / "video_outline.schema.json",
                max_tokens=4096,
            )
            _sanitize_chapter_ts(outline.get("chapters", []), duration)
            _save(video_dir, "outline.json", outline)
            print(f"[outline] {video_id}: {len(outline['chapters'])} chapters")
        except (MinimaxError, SchemaValidationError) as e:
            print(f"[warn] outline failed: {e}", file=sys.stderr)
            outline = None
            results["outline"] = f"failed: {e}"

    # 2) notes
    notes_path = video_dir / "analysis" / "notes.md"
    if not should_regen("notes") and notes_path.exists():
        print(f"[notes] {video_id}: cached")
    elif not should_regen("notes") and only is not None:
        print(f"[notes] {video_id}: skipped (only={only})", file=sys.stderr)
    else:
        try:
            notes_payload = json.dumps({
                "title": title,
                "duration_seconds": duration,
                "transcript_with_ts": transcript,
                "outline": outline,
            }, ensure_ascii=False)
            md = _call_minimax_text(
                client,
                (PROMPTS / "video_notes.md").read_text(encoding="utf-8"),
                notes_payload,
                max_tokens=6144,
            )
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            notes_path.write_text(md, encoding="utf-8")
            print(f"[notes] {video_id}: {len(md)} chars")
        except MinimaxError as e:
            print(f"[warn] notes failed: {e}", file=sys.stderr)
            results["notes"] = f"failed: {e}"

    # 3) quiz
    quiz_path = video_dir / "analysis" / "quiz.json"
    quiz_raw_path = video_dir / "analysis" / "quiz.raw.txt"
    if not should_regen("quiz") and quiz_path.exists():
        print(f"[quiz] {video_id}: cached")
    elif not should_regen("quiz") and only is not None:
        print(f"[quiz] {video_id}: skipped (only={only})", file=sys.stderr)
    else:
        notes_text = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
        try:
            quiz_payload = json.dumps({
                "title": title,
                "duration_seconds": duration,
                "transcript_with_ts": transcript,
                "outline": outline,
                "notes_markdown": notes_text,
            }, ensure_ascii=False)
            quiz = _call_minimax_json_with_retry(
                client,
                (PROMPTS / "video_quiz.md").read_text(encoding="utf-8"),
                quiz_payload,
                SCHEMAS / "video_quiz.schema.json",
                max_tokens=8192,
                raw_dump_path=quiz_raw_path,
                retries=1,
            )
            _save(video_dir, "quiz.json", quiz)
            # 成功就把 raw dump 清掉（避免误以为还失败着）
            if quiz_raw_path.exists():
                try: quiz_raw_path.unlink()
                except OSError: pass
            print(f"[quiz] {video_id}: {len(quiz['questions'])} questions")
        except (MinimaxError, SchemaValidationError) as e:
            print(f"[warn] quiz failed: {e}  (raw dumped to {quiz_raw_path.name})", file=sys.stderr)
            results["quiz"] = f"failed: {e}"

    meta["status"] = "analyzed_tutorial"
    (video_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", choices=["outline", "notes", "quiz"], default=None,
                        help="只重跑指定步骤，其余从缓存加载")
    args = parser.parse_args()
    try:
        process(args.video_id, force=args.force, only=args.only)
    except MinimaxConfigError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
