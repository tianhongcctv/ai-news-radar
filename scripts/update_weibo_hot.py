#!/usr/bin/env python3
"""Track Weibo hot-search topics as a lightweight China social-field radar.

This module deliberately stores topic-level metadata only. It does not scrape
post bodies, comments, private data, or logged-in pages. Weibo is treated as a
social signal source, not as an authoritative fact source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

UTC = timezone.utc
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_ENDPOINTS = [
    "https://weibo.com/ajax/side/hotSearch",
    "https://weibo.com/ajax/statuses/hot_band",
]

DIRECT_AI_KEYWORDS = [
    "ai", "aigc", "人工智能", "大模型", "生成式", "生成式ai", "chatgpt",
    "gpt", "openai", "deepseek", "claude", "gemini", "智能体", "agent",
    "机器人", "数字人", "换脸", "深度伪造", "deepfake", "算法", "算力",
]

STRUCTURE_KEYWORDS = [
    "就业", "裁员", "岗位", "失业", "招聘", "绩效", "劳动", "职场",
    "老师", "教师", "学生", "学校", "大学", "高校", "考试", "作弊", "论文",
    "作业", "教育", "学术", "科研", "医生", "医院", "律师", "法院", "记者",
    "客服", "程序员", "设计师", "创作者", "自媒体", "公司", "企业", "政府",
    "监管", "政策", "版权", "隐私", "诈骗", "谣言", "证据", "视频", "图片",
    "陪伴", "孤独", "情感", "恋爱", "焦虑", "心理", "孩子", "家长", "老人",
    "死亡", "逝者", "复活", "记忆", "尊严", "真实", "信任",
]

NOISE_KEYWORDS = [
    "明星", "综艺", "电视剧", "演唱会", "恋情", "分手", "结婚", "离婚", "八卦",
    "美食", "穿搭", "减肥", "带货", "直播间", "抽奖", "优惠券", "票房",
]

A_CLASS_HINTS = [
    "政府", "监管", "政策", "法院", "学校", "大学", "高校", "考试", "论文",
    "就业", "裁员", "岗位", "失业", "诈骗", "谣言", "证据", "隐私",
    "陪伴", "孤独", "焦虑", "死亡", "逝者", "医生", "教师", "学生",
]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        s = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_keyword(value: Any) -> str:
    s = re.sub(r"\s+", " ", str(value or "")).strip()
    s = s.strip("#＃")
    return s


def topic_url(keyword: str) -> str:
    # Use public search URL only; no login-only endpoint and no comment/post scraping.
    quoted = quote(f"#{keyword}#")
    return f"https://s.weibo.com/weibo?q={quoted}"


def topic_id(keyword: str) -> str:
    return "weibo-" + hashlib.sha1(keyword.strip().lower().encode("utf-8")).hexdigest()[:14]


def contains_any(text: str, keywords: list[str]) -> list[str]:
    t = text.lower()
    return [kw for kw in keywords if kw.lower() in t]


def score_topic(keyword: str) -> dict[str, Any]:
    text = keyword.lower()
    direct = contains_any(text, DIRECT_AI_KEYWORDS)
    structure = contains_any(text, STRUCTURE_KEYWORDS)
    noise = contains_any(text, NOISE_KEYWORDS)
    a_hints = contains_any(text, A_CLASS_HINTS)

    ai_relevance = 0
    civilization = 0
    if direct:
        ai_relevance += 20 + min(10, len(direct) * 2)
        civilization += 8
    if structure:
        ai_relevance += min(12, len(structure) * 2)
        civilization += 8 + min(18, len(structure) * 3)
    if a_hints:
        civilization += min(12, len(a_hints) * 2)
    if noise and not direct and len(structure) <= 1:
        civilization -= 8
        ai_relevance -= 5

    # Hidden AI-adjacent social signals: no direct AI word, but worth human review
    # when touching education, labor, public reality, or existence-layer themes.
    hidden_signal = bool(structure) and not direct
    if hidden_signal:
        civilization += 4

    return {
        "ai_relevance_score": max(0, ai_relevance),
        "civilization_score": max(0, civilization),
        "matched_ai_keywords": direct,
        "matched_structure_keywords": structure,
        "matched_noise_keywords": noise,
        "hidden_ai_adjacent_signal": hidden_signal,
    }


def parse_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(str(value).replace(",", "")))
    except Exception:
        return None


def normalize_hot_items(payload: Any) -> list[dict[str, Any]]:
    """Normalize known Weibo hot-search JSON shapes."""
    candidates: list[Any] = []
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("realtime", "hotgov", "band_list", "list"):
                if isinstance(data.get(key), list):
                    candidates.extend(data.get(key) or [])
        if isinstance(data, list):
            candidates.extend(data)
        for key in ("realtime", "hotgov", "band_list", "list"):
            if isinstance(payload.get(key), list):
                candidates.extend(payload.get(key) or [])
    elif isinstance(payload, list):
        candidates = payload

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        keyword = clean_keyword(
            item.get("word")
            or item.get("word_scheme")
            or item.get("note")
            or item.get("title")
            or item.get("name")
        )
        if not keyword or keyword in {"更多热搜", "热搜"}:
            continue
        # word_scheme may contain topic wrappers or extra labels.
        keyword = re.sub(r"^#|#$", "", keyword).strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        hot_value = parse_int(item.get("raw_hot") or item.get("num") or item.get("hot") or item.get("heat"))
        rank = parse_int(item.get("rank") or item.get("realpos") or item.get("rank_num")) or idx
        out.append(
            {
                "keyword": keyword,
                "rank": rank,
                "heat": hot_value,
                "label": item.get("label_name") or item.get("category") or item.get("icon_desc"),
                "url": topic_url(keyword),
            }
        )
    out.sort(key=lambda x: int(x.get("rank") or 9999))
    return out


def fetch_endpoint(session: requests.Session, endpoint: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    start = time.perf_counter()
    status: dict[str, Any] = {"endpoint": endpoint, "ok": False, "item_count": 0, "duration_ms": 0, "error": None}
    try:
        resp = session.get(
            endpoint,
            timeout=18,
            headers={
                "User-Agent": BROWSER_UA,
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://weibo.com/hot/search",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        items = normalize_hot_items(payload)
        status["ok"] = bool(items)
        status["item_count"] = len(items)
        if not items:
            status["error"] = "no_items_parsed"
        return items, status
    except Exception as exc:
        status["error"] = type(exc).__name__
        return [], status
    finally:
        status["duration_ms"] = int((time.perf_counter() - start) * 1000)


def fetch_weibo_hot(session: requests.Session, endpoints: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    statuses: list[dict[str, Any]] = []
    best: list[dict[str, Any]] = []
    for endpoint in endpoints:
        items, status = fetch_endpoint(session, endpoint)
        statuses.append(status)
        if len(items) > len(best):
            best = items
        if len(best) >= 30:
            break
    return best, statuses


def merge_topic_history(current: list[dict[str, Any]], previous_payload: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    prev_by_keyword = {
        str(item.get("keyword") or ""): item
        for item in previous_payload.get("hot_topics", [])
        if isinstance(item, dict) and item.get("keyword")
    }
    merged: list[dict[str, Any]] = []
    for item in current:
        keyword = item["keyword"]
        prev = prev_by_keyword.get(keyword, {})
        scores = score_topic(keyword)
        first_seen = prev.get("first_seen_at") or iso(now)
        previous_peak = parse_int(prev.get("peak_rank")) or parse_int(item.get("rank")) or 9999
        rank = parse_int(item.get("rank")) or 9999
        seen_count = (parse_int(prev.get("seen_count")) or 0) + 1
        record = {
            "topic_id": topic_id(keyword),
            "keyword": keyword,
            "rank": rank,
            "heat": item.get("heat"),
            "label": item.get("label"),
            "url": item.get("url"),
            "first_seen_at": first_seen,
            "last_seen_at": iso(now),
            "peak_rank": min(previous_peak, rank),
            "seen_count": seen_count,
            **scores,
        }
        score_total = int(record["ai_relevance_score"]) + int(record["civilization_score"])
        if score_total >= 35:
            record["suggested_level"] = "A"
            record["status"] = "watching"
        elif score_total >= 20 or record.get("hidden_ai_adjacent_signal"):
            record["suggested_level"] = "B"
            record["status"] = "watching"
        else:
            record["suggested_level"] = "C"
            record["status"] = "scan_only"
        merged.append(record)
    return merged


def update_watchlist(hot_topics: list[dict[str, Any]], previous_watch: dict[str, Any], now: datetime) -> dict[str, Any]:
    existing_items = previous_watch.get("items", []) if isinstance(previous_watch, dict) else []
    watch_by_id = {
        str(item.get("topic_id") or ""): dict(item)
        for item in existing_items
        if isinstance(item, dict) and item.get("topic_id")
    }

    active_ids = set()
    for topic in hot_topics:
        level = topic.get("suggested_level")
        if level not in {"A", "B"}:
            continue
        tid = str(topic.get("topic_id"))
        active_ids.add(tid)
        old = watch_by_id.get(tid, {})
        first_seen = old.get("first_seen_at") or topic.get("first_seen_at") or iso(now)
        first_dt = parse_iso(first_seen) or now
        tracking_days = max(1, (now.date() - first_dt.date()).days + 1)
        watch_by_id[tid] = {
            "topic_id": tid,
            "keyword": topic.get("keyword"),
            "level": old.get("level") or level,
            "suggested_level_latest": level,
            "reason": old.get("reason") or build_watch_reason(topic),
            "first_seen_at": first_seen,
            "last_seen_at": iso(now),
            "peak_rank": min(parse_int(old.get("peak_rank")) or 9999, parse_int(topic.get("peak_rank")) or 9999),
            "latest_rank": topic.get("rank"),
            "latest_heat": topic.get("heat"),
            "current_status": "active",
            "tracking_days": tracking_days,
            "url": topic.get("url"),
            "matched_ai_keywords": topic.get("matched_ai_keywords") or [],
            "matched_structure_keywords": topic.get("matched_structure_keywords") or [],
            "related_news_urls": old.get("related_news_urls") or [],
            "representative_posts": old.get("representative_posts") or [],
            "editor_note": old.get("editor_note") or "",
        }

    # Cool down or close stale topics.
    retained: list[dict[str, Any]] = []
    max_days = int(os.environ.get("WEIBO_WATCHLIST_KEEP_DAYS", "14") or "14")
    for item in watch_by_id.values():
        last_seen = parse_iso(item.get("last_seen_at")) or now
        age_hours = (now - last_seen).total_seconds() / 3600
        first_seen = parse_iso(item.get("first_seen_at")) or now
        total_age_days = (now - first_seen).days
        if item.get("topic_id") not in active_ids:
            if age_hours >= 72:
                item["current_status"] = "closed"
            elif age_hours >= 24:
                item["current_status"] = "cooling"
        if total_age_days <= max_days or item.get("current_status") != "closed":
            retained.append(item)

    retained.sort(key=lambda x: (x.get("current_status") != "active", x.get("peak_rank") or 9999, x.get("last_seen_at") or ""))
    return {
        "generated_at": iso(now),
        "source": "weibo_hot_search",
        "policy": "topic_level_metadata_only_no_post_or_comment_scraping",
        "default_tracking": "A/B topics are tracked until heat cools: 24h cooling, 72h closed if no reappearance",
        "total_items": len(retained),
        "active_items": sum(1 for i in retained if i.get("current_status") == "active"),
        "items": retained,
    }


def build_watch_reason(topic: dict[str, Any]) -> str:
    ai = "、".join(topic.get("matched_ai_keywords") or [])
    st = "、".join(topic.get("matched_structure_keywords") or [])
    parts = []
    if ai:
        parts.append(f"含AI直接信号：{ai}")
    if st:
        parts.append(f"触及文明结构词：{st}")
    if topic.get("hidden_ai_adjacent_signal"):
        parts.append("属于潜在AI相关社会现场，需人工复核")
    return "；".join(parts) or "微博热搜现场信号，需人工复核"


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Weibo hot-search field radar")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--enabled", default=os.environ.get("WEIBO_HOT_ENABLED", "1"))
    parser.add_argument("--extra-endpoint", action="append", default=[])
    args = parser.parse_args()

    now = utc_now()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    hot_path = output_dir / "weibo-hot-status.json"
    watch_path = output_dir / "weibo-watchlist.json"

    previous_hot = load_json(hot_path, {})
    previous_watch = load_json(watch_path, {})

    endpoints = list(args.extra_endpoint or [])
    env_endpoint = str(os.environ.get("WEIBO_HOT_JSON_URL") or "").strip()
    if env_endpoint:
        endpoints.insert(0, env_endpoint)
    endpoints.extend(DEFAULT_ENDPOINTS)

    if str(args.enabled).strip().lower() in {"0", "false", "no", "off"}:
        payload = {
            "generated_at": iso(now),
            "enabled": False,
            "source": "weibo_hot_search",
            "policy": "topic_level_metadata_only_no_post_or_comment_scraping",
            "endpoint_statuses": [],
            "hot_topics": [],
            "watch_candidates": [],
        }
        write_json(hot_path, payload)
        print(f"Wrote: {hot_path} (disabled)")
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": BROWSER_UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    raw_topics, endpoint_statuses = fetch_weibo_hot(session, endpoints)
    hot_topics = merge_topic_history(raw_topics, previous_hot if isinstance(previous_hot, dict) else {}, now)
    watch_candidates = [t for t in hot_topics if t.get("suggested_level") in {"A", "B"}]
    watch_payload = update_watchlist(hot_topics, previous_watch if isinstance(previous_watch, dict) else {}, now)

    payload = {
        "generated_at": iso(now),
        "enabled": True,
        "source": "weibo_hot_search",
        "policy": "topic_level_metadata_only_no_post_or_comment_scraping",
        "role": "Chinese social field radar, not authoritative fact source",
        "endpoint_statuses": endpoint_statuses,
        "successful_endpoints": sum(1 for s in endpoint_statuses if s.get("ok")),
        "failed_endpoints": [s.get("endpoint") for s in endpoint_statuses if not s.get("ok")],
        "total_hot_topics": len(hot_topics),
        "watch_candidate_count": len(watch_candidates),
        "hot_topics": hot_topics,
        "watch_candidates": watch_candidates,
    }

    write_json(hot_path, payload)
    write_json(watch_path, watch_payload)
    print(f"Wrote: {hot_path} ({len(hot_topics)} hot topics, {len(watch_candidates)} watch candidates)")
    print(f"Wrote: {watch_path} ({watch_payload.get('total_items', 0)} tracked topics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
