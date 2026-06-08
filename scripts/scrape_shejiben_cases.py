"""
设计本（shejiben.com）真实装修案例直爬 —— 每个案例 = 一个带成套实拍图的"原帖"。

设计本是服务端渲染，案例页 URL 形如 /sjs/<设计师id>/case-<案例id>-1.html，
案例图在 pic*.shejiben.com/td/sjbCase/<hash>.jpg。无干净列表页，但案例页互链，
故用 BFS 从首页滚雪球。每页同时：① 抽图集做输出 ② 发现更多案例链接入队。

输出 JSONL，每行一个案例（多图），供 build_discover_index.py 直接消费：
  {source_type:"shejiben", title, source_url, site, area, images:[url...],
   tags:{style:[],space:[]}, fetched_at}

务实风险：设计站可能改版/限频/图床防盗链。失败的案例跳过、不阻塞。
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ_CN = timezone(timedelta(hours=8))
HOME = "https://www.shejiben.com/"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.shejiben.com/",
}

STYLE_VOCAB = ["原木", "现代简约", "温暖简约", "奶油风", "简约", "侘寂", "法式", "北欧",
               "现代", "中式", "新中式", "欧式", "美式", "日式", "轻奢", "工业"]
# 把站点常见风格词归一到我们的 8 类词表
STYLE_CANON = {
    "现代": "现代简约", "中式": "侘寂", "新中式": "侘寂", "日式": "原木",
    "欧式": "法式", "美式": "法式", "轻奢": "现代简约", "工业": "简约",
}
CANON_SET = ["原木", "现代简约", "温暖简约", "奶油风", "简约", "侘寂", "法式", "北欧"]
SPACE_VOCAB = ["儿童房", "客厅", "厨房", "餐厅", "餐边柜", "主卧", "卧室", "卫生间",
               "阳台", "玄关", "衣帽间", "书房", "次卧"]
SPACE_CANON = {"卧室": "主卧", "次卧": "主卧", "书房": "衣帽间"}
CASE_RE = re.compile(r"/sjs/\d+/case-\d+-1\.html")
PHOTO_RE = re.compile(r"https?://[^\"'\s)]+?/td/sjbCase/[^\"'\s)]+?\.(?:jpg|jpeg|webp)")


def now_iso():
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(600000).decode("utf-8", "replace")
    except Exception as e:
        print(f"[skip] {url} -> {type(e).__name__}: {str(e)[:60]}", file=sys.stderr)
        return None


def find_case_links(html):
    out = set()
    for m in CASE_RE.findall(html):
        out.add("https://www.shejiben.com" + m)
    return out


def canon_styles(found):
    out = []
    for s in found:
        c = STYLE_CANON.get(s, s)
        if c in CANON_SET and c not in out:
            out.append(c)
    return out


def canon_spaces(found):
    out = []
    for s in found:
        c = SPACE_CANON.get(s, s)
        if c in SPACE_VOCAB[:11] and c not in out:  # 只留规范空间词
            out.append(c)
    return out


def parse_case(url, html):
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    title_full = (title_m.group(1) if title_m else "").strip()
    # 完整标题形如「<案例名>_效果图 - 装修风格 北欧 - 设计本」，风格在被截掉的尾部，需先从完整标题提风格
    title = re.sub(r"\s*[-_]\s*(效果图|设计本|装修案例).*$", "", title_full).strip() or "装修案例"

    photos = []
    for p in PHOTO_RE.findall(html):
        if p not in photos:
            photos.append(p)
    photos = photos[:24]

    # 风格主要看标题，空间看全文（照片说明里常出现客厅/卧室等）
    styles = canon_styles([s for s in STYLE_VOCAB if s in title_full]) or canon_styles([s for s in STYLE_VOCAB if s in html[:8000]])
    spaces = canon_spaces([s for s in SPACE_VOCAB if s in html])
    area_m = re.search(r"(\d{2,4})\s*(?:平米|㎡|平)", title + html[:4000])
    area = int(area_m.group(1)) if area_m else None

    return {
        "source_type": "shejiben",
        "title": title,
        "source_url": url,
        "site": "www.shejiben.com",
        "area": area,
        "images": photos,
        "tags": {"style": styles, "space": spaces},
        "fetched_at": now_iso(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/raw/shejiben_cases.jsonl")
    ap.add_argument("--max-cases", type=int, default=60)
    ap.add_argument("--min-photos", type=int, default=4)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    home = fetch(HOME)
    if not home:
        print("[error] 首页拉取失败，终止", file=sys.stderr)
        return 1
    queue = deque(find_case_links(home))
    seen = set(queue)
    print(f"[seed] 首页种子案例 {len(queue)} 个", file=sys.stderr)

    out = []
    while queue and len(out) < args.max_cases:
        url = queue.popleft()
        html = fetch(url)
        if not html:
            time.sleep(args.sleep)
            continue
        case = parse_case(url, html)
        if len(case["images"]) >= args.min_photos:
            out.append(case)
            print(f"[case] {len(out)}/{args.max_cases} {case['title'][:24]} | {len(case['images'])}图 | 风格{case['tags']['style']} 空间{case['tags']['space']}", file=sys.stderr)
        for c in find_case_links(html):
            if c not in seen:
                seen.add(c)
                queue.append(c)
        time.sleep(args.sleep)

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in out), encoding="utf-8")
    print(f"\n[done] {len(out)} 个案例 -> {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
