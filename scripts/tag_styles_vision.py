"""
视觉风格标注 —— 让 VL 模型「看图」给缺风格的 item 补风格标签。

设计本案例（及部分 360 图）标题里没有风格，纯文本推断不出。此脚本下载封面图、
base64 送 Minimax 视觉接口（实测 abab6.5s-chat / MiniMax-Text-01 走 image_url 能真看图；
M2.7 不行），从 8 类风格词表里选 1-3 个，写入 side-file data/vision_style_tags.json
（key=content_hash），由 build_discover_index.py 合并。带缓存，重跑只补新的、不重复花钱。

用法：
  python scripts/build_discover_index.py            # 先构建（缺风格的会是空）
  python scripts/tag_styles_vision.py --limit 60    # 看图补风格 -> side-file
  python scripts/build_discover_index.py            # 再构建，风格被合并进去
"""
import argparse
import base64
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minimax_client import MinimaxClient, MinimaxError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "discover_index.json"
SIDE_PATH = PROJECT_ROOT / "data" / "vision_style_tags.json"
TZ_CN = timezone(timedelta(hours=8))

STYLE_VOCAB = ["原木", "现代简约", "温暖简约", "奶油风", "简约", "侘寂", "法式", "北欧"]
VISION_MODEL = "abab6.5s-chat"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}

PROMPT = (
    "你是室内设计风格鉴别专家。仔细看这张装修实拍照片本身（材质、色调、线条、软装、灯光），"
    "从下面 8 个风格里选 1-3 个最贴切的（按贴切度从高到低排序）：\n"
    "原木、现代简约、温暖简约、奶油风、简约、侘寂、法式、北欧。\n"
    "只依据图片本身判断，不要凭空猜。只回一个 JSON：{\"style\":[\"...\"]}"
)


def now_iso():
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


def fetch_image_bytes(cover):
    if cover.get("kind") == "local":
        p = PROJECT_ROOT / cover["src"]
        return p.read_bytes() if p.exists() else None
    try:
        req = urllib.request.Request(cover["src"], headers=UA)  # 无 referer，绕设计本防盗链
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except Exception as e:
        print(f"[skip] 下载失败 {cover.get('src','')[:50]} -> {type(e).__name__}", file=sys.stderr)
        return None


def vision_call(client, img_bytes, model, retries=1):
    b64 = base64.b64encode(img_bytes).decode()
    url = client.base_url + "/text/chatcompletion_v2"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
        ]}],
        "max_tokens": 200,
        "temperature": 0.1,
    }
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + client.api_key}
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
            ch = (j.get("choices") or [{}])[0].get("message", {}).get("content")
            if not ch:
                last = MinimaxError("empty content")
                continue
            s = ch.strip()
            if s.startswith("```"):
                s = s.strip("`")
                if s.lower().startswith("json"):
                    s = s[4:]
            a, b = s.find("{"), s.rfind("}")
            obj = json.loads(s[a:b + 1]) if a != -1 and b != -1 else {}
            styles = [t for t in (obj.get("style") or []) if t in STYLE_VOCAB]
            return styles[:3]
        except Exception as e:
            last = e
            time.sleep(1.5)
    print(f"[warn] 视觉调用失败: {str(last)[:80]}", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=80, help="本次最多标注多少个")
    ap.add_argument("--model", default=VISION_MODEL)
    ap.add_argument("--all", action="store_true", help="对所有 item 重标（默认只补缺风格的）")
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    items = index.get("items", [])
    side = {}
    if SIDE_PATH.exists():
        side = json.loads(SIDE_PATH.read_text(encoding="utf-8"))

    targets = []
    for it in items:
        has_style = bool(it.get("tags", {}).get("style"))
        ch = it.get("content_hash")
        if not ch:
            continue
        if args.all or (not has_style and ch not in side):
            targets.append(it)
    print(f"待标注 {len(targets)} 个（已缓存 {len(side)}），本次上限 {args.limit}", file=sys.stderr)

    client = MinimaxClient()
    done = 0
    for it in targets[: args.limit]:
        img = fetch_image_bytes(it["cover"])
        if not img:
            continue
        styles = vision_call(client, img, args.model)
        if styles is None:
            continue
        side[it["content_hash"]] = {"style": styles, "source_type": it.get("source_type"), "tagged_at": now_iso()}
        done += 1
        print(f"[{done}] {it.get('title','')[:24]} -> {styles}", file=sys.stderr)
        SIDE_PATH.write_text(json.dumps(side, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(args.sleep)

    print(f"\n[done] 本次新标注 {done} 个 -> {SIDE_PATH}（累计 {len(side)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
