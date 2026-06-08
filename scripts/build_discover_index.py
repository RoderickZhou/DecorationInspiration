"""
合并多源 -> data/discover_index.json（发现流统一内容池）。

源 1（视频）：每个 style 类视频 = 一个多帧"案例"
  读 data/videos/<id>/meta.json (classification.type=="style") + analysis/captions.json
  封面=首帧(local)，gallery=全部帧(带 caption/design_points/ts)。

源 2（爬图）：每条已结构化的候选 = 一个单图案例
  读 data/normalized/item_structuring.*.outputs.jsonl
  封面=candidate.cover_url(remote)，tags/summary/fit_score 来自 output。

与 process_inbox.rebuild_style_index 共存、不替换。产物供 demo/discover.html 消费。
"""
import argparse
import glob
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema_validate import load_schema, validate_or_raise, SchemaValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"
NORMALIZED_DIR = PROJECT_ROOT / "data" / "normalized"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "discover_item.schema.json"

TZ_CN = timezone(timedelta(hours=8))

STYLE_VOCAB = ["原木", "现代简约", "温暖简约", "奶油风", "简约", "侘寂", "法式", "北欧"]
SPACE_VOCAB = ["儿童房", "客厅", "厨房", "餐厅", "餐边柜", "主卧", "卫生间", "阳台", "玄关", "衣帽间"]

# candidate.platform -> DiscoverItem.source_type
PLATFORM_MAP = {
    "360image": "so360",
    "bing": "bing",
    "shejiben": "shejiben",
    "to8to": "to8to",
    "unsplash": "unsplash",
    "pexels": "pexels",
}


def now_iso() -> str:
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def keep_vocab(values, vocab):
    """保留落在词表内的标签，去重保序。"""
    out = []
    vset = set(vocab)
    for t in values or []:
        if t in vset and t not in out:
            out.append(t)
    return out


def media_local(rel_path: str) -> dict:
    return {"kind": "local", "src": rel_path}


def media_remote(url: str) -> dict:
    return {"kind": "remote", "src": url}


def all_video_ids():
    ids = []
    if VIDEOS_DIR.exists():
        for d in VIDEOS_DIR.iterdir():
            if d.is_dir() and d.name != "inbox" and (d / "meta.json").exists():
                ids.append(d.name)
    return sorted(ids)


def build_video_items():
    items = []
    for vid in all_video_ids():
        d = VIDEOS_DIR / vid
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        if (meta.get("classification") or {}).get("type") != "style":
            continue
        cap_path = d / "analysis" / "captions.json"
        if not cap_path.exists():
            continue
        try:
            cap = json.loads(cap_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        frames = cap.get("frames") or []
        if not frames:
            continue
        overall = cap.get("overall") or {}

        def frame_media(fr):
            return media_local(f"data/videos/{vid}/frames/{fr.get('path')}")

        gallery = []
        styles, spaces = list(overall.get("style_tags") or []), list(overall.get("space_tags") or [])
        for fr in frames:
            g = {"img": frame_media(fr)}
            if fr.get("caption"):
                g["caption"] = fr["caption"]
            if fr.get("design_points"):
                g["design_points"] = fr["design_points"]
            if fr.get("ts") is not None:
                g["ts"] = fr["ts"]
            gallery.append(g)
            ftags = fr.get("tags") or {}
            styles += ftags.get("style") or []
            spaces += ftags.get("space") or []

        headline = (meta.get("style_overall") or {}).get("headline") or ""
        item = {
            "item_id": f"video:{vid}",
            "source_type": "video",
            "title": headline or cap.get("title") or meta.get("title") or vid,
            "cover": frame_media(frames[0]),
            "tags": {
                "style": keep_vocab(styles, STYLE_VOCAB),
                "space": keep_vocab(spaces, SPACE_VOCAB),
                "features": [],
            },
            "gallery": gallery,
            "video_id": vid,
            "content_hash": "video:" + sha1(vid)[:16],
            "ingested_at": meta.get("ingested_at") or now_iso(),
        }
        if headline:
            item["summary"] = headline
        items.append(item)
    return items


def build_image_items():
    items = []
    files = sorted(glob.glob(str(NORMALIZED_DIR / "item_structuring.*.outputs.jsonl")))
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            cand = row.get("candidate") or {}
            out = row.get("output") or {}
            cover_url = cand.get("cover_url") or (cand.get("image_urls") or [None])[0]
            if not cover_url:
                continue
            platform = cand.get("platform") or "360image"
            st = PLATFORM_MAP.get(platform, "so360")
            src_url = cand.get("source_url") or cover_url
            tags = out.get("tags") or {}
            cover = media_remote(cover_url)
            item = {
                "item_id": f"{st}:{sha1(st + '|' + src_url)[:16]}",
                "source_type": st,
                "title": cand.get("title") or "装修灵感",
                "cover": cover,
                "tags": {
                    "style": keep_vocab(tags.get("style"), STYLE_VOCAB),
                    "space": keep_vocab(tags.get("space"), SPACE_VOCAB),
                    "features": (tags.get("features") or [])[:6],
                },
                "gallery": [{"img": cover}],
                "source_url": src_url,
                "site": cand.get("author") or "",
                "content_hash": sha1(cover_url),
                "ingested_at": cand.get("published_at") or now_iso(),
                "license": {
                    "type": "web-thumbnail",
                    "source_page": src_url,
                    "note": "搜索引擎缩略图，点击跳原站查看",
                },
            }
            if out.get("summary"):
                item["summary"] = out["summary"]
            if isinstance(out.get("fit_score"), (int, float)):
                item["fit_score"] = out["fit_score"]
            items.append(item)
    return items


def build_shejiben_cases():
    """设计本案例：每个 = 一个带成套实拍图的多图案例（真案例页 source_url）。"""
    items = []
    files = sorted(glob.glob(str(RAW_DIR / "shejiben_cases*.jsonl")))
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except Exception:
                continue
            imgs = c.get("images") or []
            if not imgs:
                continue
            src = c.get("source_url") or imgs[0]
            styles = keep_vocab((c.get("tags") or {}).get("style"), STYLE_VOCAB)
            spaces = keep_vocab((c.get("tags") or {}).get("space"), SPACE_VOCAB)
            bits = []
            if c.get("area"):
                bits.append(f"{c['area']}㎡")
            if styles:
                bits.append("/".join(styles))
            bits.append("实拍案例")
            items.append({
                "item_id": "shejiben:" + sha1(src)[:16],
                "source_type": "shejiben",
                "title": c.get("title") or "设计本装修案例",
                "summary": " · ".join(bits),
                "cover": media_remote(imgs[0]),
                "tags": {"style": styles, "space": spaces, "features": []},
                "gallery": [{"img": media_remote(u)} for u in imgs[:24]],
                "source_url": src,
                "site": c.get("site") or "www.shejiben.com",
                "content_hash": sha1(src),
                "ingested_at": c.get("fetched_at") or now_iso(),
                "license": {"type": "web-case", "source_page": src, "note": "设计本设计师案例实拍，点击看原案例全部照片"},
            })
    return items


def dedupe(items):
    """按 content_hash 去重，冲突保留 gallery 更长者（视频案例优先）。"""
    by_hash = {}
    order = []
    for it in items:
        h = it["content_hash"]
        if h not in by_hash:
            by_hash[h] = it
            order.append(h)
        elif len(it["gallery"]) > len(by_hash[h]["gallery"]):
            by_hash[h] = it
    return [by_hash[h] for h in order]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(PROJECT_ROOT / "data" / "discover_index.json"))
    ap.add_argument("--videos-only", action="store_true")
    ap.add_argument("--images-only", action="store_true")
    args = ap.parse_args()

    items = []
    if not args.images_only:
        items += build_video_items()
    if not args.videos_only:
        items += build_shejiben_cases()
        items += build_image_items()
    items = dedupe(items)

    # 合并视觉风格标签（tag_styles_vision.py 看图补的，只填给缺风格的 item）
    vfilled = 0
    vpath = PROJECT_ROOT / "data" / "vision_style_tags.json"
    if vpath.exists():
        try:
            vision = json.loads(vpath.read_text(encoding="utf-8"))
        except Exception:
            vision = {}
        for it in items:
            if not it["tags"]["style"] and it["content_hash"] in vision:
                vs = keep_vocab(vision[it["content_hash"]].get("style"), STYLE_VOCAB)
                if vs:
                    it["tags"]["style"] = vs
                    vfilled += 1

    index = {"schema_version": "v1", "generated_at": now_iso(), "items": items}

    try:
        validate_or_raise(index, load_schema(SCHEMA_PATH), SCHEMA_PATH)
    except SchemaValidationError as e:
        print(f"[warn] schema 校验未过: {e}", file=sys.stderr)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    by_src = Counter(it["source_type"] for it in items)
    video_n = sum(1 for it in items if it["source_type"] == "video")
    with_style = sum(1 for it in items if it["tags"]["style"])
    print(f"[discover] {len(items)} items -> {out}")
    print(f"  视频案例: {video_n} | 图片: {len(items) - video_n} | 有风格标签: {with_style}/{len(items)}（其中视觉补 {vfilled}）")
    print(f"  按来源: {dict(by_src)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
