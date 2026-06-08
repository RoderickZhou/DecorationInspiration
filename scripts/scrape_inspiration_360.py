"""
装修灵感图采集器 — 数据源：360 图片搜索 JSON API。

为什么用 360 图片：
- 国内网络可直达（不像 Unsplash / Pexels）
- 公开 JSON 接口 image.so.com/j，无需登录、参数简单
- 返回的图片来自全网真实站点（含设计本、土巴兔、好好住、新浪家居等），
  缩略图走 360 自家 CDN（qhimgs1）稳定可加载，原页 URL 可点击跳转
- 用于 lookbook MVP，给出"按空间分类的海量真图"基础数据

后续接好好住 / 小红书 / Pinterest 真实采集器时，这个脚本可以下线，
但本文件本身和它产出的 JSONL schema 保持稳定。
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


TZ_CN = timezone(timedelta(hours=8))

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# 空间 → 多组关键词（每组当成独立查询，结果合并去重）
SPACE_QUERIES: Dict[str, List[str]] = {
    "儿童房": [
        "儿童房 装修 实景",
        "儿童房 二孩 实景图",
        "儿童房 收纳 男孩",
        "儿童房 学龄 学习区",
        "儿童房 一睡一玩",
    ],
    "客厅": [
        "客厅 装修 实景",
        "客厅 功能角 实景",
        "客厅 整墙收纳",
        "客厅 沙发墙 实景",
        "客厅 阅读角",
    ],
    "厨房": [
        "厨房 装修 实景",
        "厨房 餐边柜 实景",
        "开放厨房 实景",
        "厨房 收纳 实景",
        "厨房 中岛 实景图",
    ],
    "收纳": [
        "全屋收纳 实景",
        "玄关 收纳 实景",
        "餐边柜 收纳 实景",
        "衣帽间 实景",
        "嵌入式 收纳柜",
    ],
    "主卧": [
        "主卧 装修 实景",
        "主卧 衣帽间 实景",
        "主卧 飘窗 实景",
        "主卧 床头 实景",
    ],
}


def fetch_360_images(query: str, pn: int = 30, sn: int = 0) -> List[Dict[str, Any]]:
    url = (
        "https://image.so.com/j"
        f"?q={urllib.parse.quote(query)}&src=srp"
        f"&sn={sn}&pn={pn}&adstar=0"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": "https://image.so.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        print(f"[warn] query '{query}' failed: {e}", file=sys.stderr)
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[warn] query '{query}' returned non-JSON", file=sys.stderr)
        return []
    return data.get("list") or []


def now_iso() -> str:
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


def to_raw_item(space: str, query: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """把 360 单条搜索结果转成 raw_collector_item.schema 兼容的对象。"""
    # 优先用 HTTPS 缩略图，避免浏览器混合内容警告
    image_url = (item.get("thumb_bak") or item.get("img") or item.get("link") or "").strip()
    if image_url.startswith("http://"):
        image_url = "https://" + image_url[len("http://") :]

    title = (item.get("title") or "").strip()
    if not title:
        title = f"{space}装修参考"
    # 把搜索词织进 text，让 Minimax 有更多上下文判 fit
    content_text = f"{title}。空间方向：{space}。检索词：{query}。来源站点：{item.get('dspurl', '')}"

    # 用原页 purl 作为可点击跳转地址，缺失则用图片本身
    canonical_url = (item.get("purl") or "").strip() or image_url

    width = _safe_int(item.get("width"))
    height = _safe_int(item.get("height"))

    return {
        "platform": "360image",
        "canonical_url": canonical_url,
        "fetched_at": now_iso(),
        "title": title,
        "author": (item.get("site") or item.get("dspurl") or "网络").strip(),
        "published_at": now_iso(),
        "content_text": content_text,
        "images": [
            {
                "url": image_url,
                "width": width,
                "height": height,
            }
        ],
        "metrics": {},
        "raw": {
            "json": {
                "search_space": space,
                "search_query": query,
                "id": item.get("id"),
                "site": item.get("site"),
                "dspurl": item.get("dspurl"),
                "purl": item.get("purl"),
                "source_code": item.get("source"),
            }
        },
    }


def _safe_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="raw collector JSONL path")
    parser.add_argument("--per-query", type=int, default=30, help="images per query (max 60)")
    parser.add_argument("--sleep", type=float, default=0.4, help="seconds between queries")
    parser.add_argument(
        "--min-resolution",
        type=int,
        default=400,
        help="minimum width OR height to keep (filters out tiny thumbnails)",
    )
    parser.add_argument(
        "--skip-aigc",
        action="store_true",
        help="filter out 360 'copyright_text_aigc' results (likely AI-generated)",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    seen_urls: set = set()
    rows: List[Dict[str, Any]] = []
    space_counts: Dict[str, int] = {}

    for space, queries in SPACE_QUERIES.items():
        for query in queries:
            print(f"[query] space={space}  q={query}", file=sys.stderr)
            results = fetch_360_images(query, pn=args.per_query)
            kept = 0
            for item in results:
                if args.skip_aigc and (item.get("source") or "") == "copyright_text_aigc":
                    continue
                w = _safe_int(item.get("width"))
                h = _safe_int(item.get("height"))
                if max(w, h) < args.min_resolution:
                    continue
                raw_item = to_raw_item(space, query, item)
                image_url = raw_item["images"][0]["url"]
                if not image_url or image_url in seen_urls:
                    continue
                seen_urls.add(image_url)
                rows.append(raw_item)
                kept += 1
            space_counts[space] = space_counts.get(space, 0) + kept
            print(f"  -> kept {kept} (total {len(rows)})", file=sys.stderr)
            time.sleep(args.sleep)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(rows)} items to {out_path}")
    for space, n in space_counts.items():
        print(f"  {space}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
