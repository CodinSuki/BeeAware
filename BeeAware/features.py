"""Shared feature builders for global safe learning and local personal learning."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

FEATURE_VERSION = "safe-v1"
SIGNAL_GROUPS = {
    "urgent": ("urgent", "deadline", "due", "critical", "emergency"),
    "project": ("project", "task", "issue", "ticket", "milestone"),
    "meeting": ("meeting", "calendar", "conference", "standup", "zoom", "teams"),
    "learning": ("course", "lesson", "tutorial", "study", "assignment", "research"),
    "game": ("game", "games", "gaming", "steam", "play", "minecraft", "terraria", "roblox", "fortnite"),
    "media": ("youtube", "netflix", "video", "music", "stream", "spotify"),
    "dev": ("github", "gitlab", "stackoverflow", "code", "debug", "repository", "programming"),
    "finance": ("bank", "finance", "invoice", "payment", "budget", "accounting"),
}


def _contains_signal(text: str, terms: tuple[str, ...]) -> int:
    return int(any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms))


def build_safe_feature_text(exe_name: str, raw_title: str, source_type: str,
                            browser_category: str, browser_domain: str,
                            app_family: str) -> str:
    title = (raw_title or "").lower()
    exe = exe_name.lower().replace(".exe", "").strip()
    fields = [
        f"process={exe}", f"source={source_type}",
        f"browser_category={browser_category}", f"browser_domain={browser_domain}",
        f"app_family={app_family}",
    ]
    fields.extend(
        f"has_{name}_word={_contains_signal(title, terms)}"
        for name, terms in SIGNAL_GROUPS.items()
    )
    fields.extend([
        f"title_length_bucket={min(len(raw_title or '') // 20, 10)}",
        f"word_count_bucket={min(len(title.split()) // 5, 10)}",
    ])
    return " | ".join(fields)


def build_training_feature_text(row: Mapping) -> str:
    fields = [
        ("process", row.get("process_name", "unknown")),
        ("source", row.get("source_type", "unknown")),
        ("browser_category", row.get("browser_category", "unknown")),
        ("browser_domain", row.get("browser_domain", "unknown")),
        ("app_family", row.get("app_family", "unknown")),
    ]
    for name in SIGNAL_GROUPS:
        fields.append((f"has_{name}_word", row.get(f"has_{name}_word", 0)))
    title_length = float(row.get("title_length", 0) or 0)
    word_count = float(row.get("word_count", 0) or 0)
    fields.extend([
        ("title_length_bucket", min(int(title_length) // 20, 10)),
        ("word_count_bucket", min(int(word_count) // 5, 10)),
    ])
    return " | ".join(f"{key}={value}" for key, value in fields)


def build_personal_feature_text(safe_features: str, raw_title: str) -> str:
    return f"{safe_features} | title_context={raw_title or ''}"


def build_title_override_key(exe_name: str, source_type: str, browser_category: str,
                             browser_domain: str, app_family: str, raw_title: str) -> str:
    context = "|".join((exe_name.lower(), source_type, browser_category, browser_domain, app_family))
    title = " ".join((raw_title or "").lower().split())
    digest = hashlib.sha256(f"{context}|{title}".encode("utf-8")).hexdigest()
    return f"title_override_v1:{digest}"
