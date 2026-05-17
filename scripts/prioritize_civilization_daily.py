#!/usr/bin/env python3
"""Prioritize AI civilization signals and cap the homepage daily list.

This script runs after scripts/update_news.py. It keeps the full raw/all-mode
payloads for research, but limits the homepage AI list to the highest-signal
civilization-observation items.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc

PRIORITY_KEYWORDS: list[tuple[str, int]] = [
    # Knowledge and education
    ("知识", 6), ("教育", 6), ("学习", 5), ("学校", 5), ("大学", 5),
    ("教师", 6), ("学生", 5), ("课堂", 5), ("考试", 4), ("论文", 4),
    ("research", 4), ("science", 4), ("education", 6), ("school", 5),
    ("teacher", 6), ("student", 5), ("university", 5),

    # Work and professions
    ("职业", 7), ("就业", 7), ("工作", 6), ("劳动", 6), ("岗位", 6),
    ("白领", 5), ("程序员", 5), ("医生", 6), ("律师", 6), ("记者", 6),
    ("job", 7), ("jobs", 7), ("work", 6), ("worker", 6), ("labor", 6),
    ("profession", 7), ("developer", 4), ("journalist", 6), ("doctor", 6),
    ("lawyer", 6),

    # Organization and production
    ("组织", 7), ("企业", 5), ("公司", 4), ("管理", 5), ("生产力", 5),
    ("自动化", 5), ("流程", 5), ("办公", 5), ("团队", 4),
    ("organization", 7), ("enterprise", 5), ("company", 4), ("management", 5),
    ("productivity", 5), ("automation", 5), ("workflow", 5), ("office", 5),

    # Institutions, law and governance
    ("制度", 8), ("政策", 7), ("监管", 8), ("法律", 8), ("法院", 8),
    ("版权", 8), ("隐私", 7), ("安全", 5), ("治理", 7), ("伦理", 7),
    ("责任", 6), ("政府", 6), ("国家", 5),
    ("policy", 7), ("regulation", 8), ("regulatory", 8), ("law", 8),
    ("legal", 8), ("court", 8), ("copyright", 8), ("privacy", 7),
    ("governance", 7), ("ethics", 7), ("responsibility", 6), "government", 6,

    # Society and relationships
    ("社会", 6), ("关系", 6), ("家庭", 5), ("陪伴", 7), ("情感", 7),
    ("孤独", 8), ("身份", 6), ("信任", 6), ("社区", 5),
    ("society", 6), ("relationship", 6), ("family", 5), ("companion", 7),
    ("emotional", 7), ("loneliness", 8), ("identity", 6), ("trust", 6),

    # Media, creation and meaning
    ("媒体", 6), ("新闻", 6), ("内容", 5), ("创作", 5), ("创造", 5),
    ("艺术", 4), ("意义", 8), ("存在", 8), ("人类", 7), ("文明", 9),
    ("media", 6), ("news", 6), ("content", 5), ("creator", 5), ("creative", 5),
    ("meaning", 8), ("existence", 8), ("human", 7), ("civilization", 9),
]

LOW_SIGNAL_KEYWORDS = [
    "release", "released", "launch", "launched", "benchmark", "排行榜",
    "融资", "funding", "price", "coupon", "discount", "促销", "优惠",
    "插件", "更新日志", "changelog", "sdk", "api", "github", "paper",
]

HIGH_VALUE_SOURCES = [
    "OpenAI", "Anthropic", "Google DeepMind", "MIT Technology Review", "Wired",
    "The Verge AI", "Inside Higher Ed", "OECD", "NIST", "Ars Technica AI",
    "InfoQ", "少数派", "宝玉", "Simon Willison",
]


def parse_dt(value: Any) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return datetime.min.replace(tzinfo=UTC)


def text_for_item(item: dict[str, Any]) -> str:
    parts = [
        item.get("title_zh"), item.get("title_bilingual"), item.get("title"),
        item.get("title_original"), item.get("source"), item.get("site_name"), item.get("url"),
    ]
    return " ".join(str(p or "") for p in parts).lower()


def score_item(item: dict[str, Any]) -> tuple[int, float, str]:
    text = text_for_item(item)
    score = 0
    matched: list[str] = []

    for keyword, weight in PRIORITY_KEYWORDS:
        if keyword.lower() in text:
            score += weight
            matched.append(keyword)

    source_text = f"{item.get('source') or ''} {item.get('site_name') or ''}"
    if any(src.lower() in source_text.lower() for src in HIGH_VALUE_SOURCES):
        score += 4

    # Prefer items that have already survived AI filtering but avoid pure product-log noise.
    if str(item.get("site_id") or "") in {"official_ai", "opmlrss", "aibreakfast", "aihubtoday", "aibase", "aihot"}:
        score += 2

    if any(k.lower() in text for k in LOW_SIGNAL_KEYWORDS):
        score -= 2

    published = parse_dt(item.get("published_at") or item.get("first_seen_at") or item.get("last_seen_at"))
    return score, published.timestamp(), ",".join(matched[:8])


def cap_and_rank(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    enriched: list[tuple[tuple[int, float, str], dict[str, Any]]] = []
    for item in items:
        score, timestamp, matched = score_item(item)
        out = dict(item)
        out["civilization_score"] = score
        if matched:
            out["civilization_keywords"] = matched
        enriched.append(((score, timestamp, str(out.get("id") or "")), out))

    enriched.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in enriched[:limit]]


def recompute_site_stats(items: list[dict[str, Any]], previous_stats: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    raw_by_site = {str(s.get("site_id")): int(s.get("raw_count") or s.get("count") or 0) for s in previous_stats or []}
    names = {str(s.get("site_id")): str(s.get("site_name") or s.get("site_id")) for s in previous_stats or []}
    stats: dict[str, dict[str, Any]] = {}
    for item in items:
        sid = str(item.get("site_id") or "unknown")
        name = str(item.get("site_name") or names.get(sid) or sid)
        if sid not in stats:
            stats[sid] = {"site_id": sid, "site_name": name, "count": 0, "raw_count": raw_by_site.get(sid, 0)}
        stats[sid]["count"] += 1
    return sorted(stats.values(), key=lambda x: x["count"], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cap and prioritize AI civilization daily items")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    latest_path = data_dir / "latest-24h.json"
    latest_all_path = data_dir / "latest-24h-all.json"

    if not latest_path.exists():
        print(f"Missing {latest_path}; nothing to prioritize")
        return 0

    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    all_payload = {}
    if latest_all_path.exists():
        all_payload = json.loads(latest_all_path.read_text(encoding="utf-8"))

    source_items = latest.get("items_ai") or latest.get("items") or []
    if not isinstance(source_items, list):
        source_items = []

    ranked_items = cap_and_rank(source_items, max(1, int(args.limit)))

    previous_total = latest.get("total_items")
    previous_ai_raw = latest.get("total_items_ai_raw")
    previous_stats = latest.get("site_stats") if isinstance(latest.get("site_stats"), list) else []

    latest["daily_item_limit"] = int(args.limit)
    latest["selection_policy"] = "civilization_structure_keywords_first"
    latest["total_items_before_daily_cap"] = previous_total
    latest["total_items"] = len(ranked_items)
    latest["items"] = ranked_items
    latest["items_ai"] = ranked_items
    latest["site_stats"] = recompute_site_stats(ranked_items, previous_stats)
    latest["site_count"] = len(latest["site_stats"])
    latest["source_count"] = len({f"{i.get('site_id')}::{i.get('source')}" for i in ranked_items})
    if previous_ai_raw is not None:
        latest["total_items_ai_raw"] = previous_ai_raw

    # Keep all-mode data intact, but add metadata so researchers know the homepage is capped.
    if all_payload:
        all_payload["daily_item_limit"] = int(args.limit)
        all_payload["selection_policy"] = "homepage_items_capped_after_civilization_priority_ranking"
        latest_all_path.write_text(json.dumps(all_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prioritized homepage items: {len(source_items)} -> {len(ranked_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
