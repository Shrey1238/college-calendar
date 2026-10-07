#!/usr/bin/env python3
"""Collect college calendar events into events.json.

Sources:
  - Canvas iCal feed(s): set CANVAS_ICS_URL (comma-separated if several). The
    feed URL embeds your Canvas token, so keep it in a secret, not in the repo.
  - manual.yaml: hand-curated events (exams, registrar dates, anything Canvas
    doesn't expose). See manual.yaml for the format.
  - courses.yaml: course display names, colors, and keywords used to tag
    Canvas events with the right course.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

import yaml
from icalendar import Calendar

EVENT_TYPES = [
    ("final", re.compile(r"\bfinal\b", re.I)),
    ("exam", re.compile(r"\b(exam|midterm|quiz|test)\b", re.I)),
    ("assignment", re.compile(r".", re.S)),
]


def classify(title: str) -> str:
    for kind, pattern in EVENT_TYPES:
        if pattern.search(title):
            return kind
    return "assignment"


def to_iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


def match_course(text: str, courses: dict) -> str | None:
    """Return the course key whose name/keywords appear in `text`."""
    low = text.lower()
    for key, cfg in courses.items():
        needles = [key] + list(cfg.get("keywords", []))
        if any(n.lower() in low for n in needles):
            return key
    return None


TAG_RE = re.compile(r"\s*\[([^\]]+)\]\s*$")


def canvas_events(courses: dict) -> list[dict]:
    urls = [u.strip() for u in os.environ.get("CANVAS_ICS_URL", "").split(",") if u.strip()]
    if not urls:
        print("CANVAS_ICS_URL not set; skipping Canvas")
        return []
    out = []
    for i, url in enumerate(urls):
        try:
            cal = Calendar.from_ical(requests_get(url, binary=True))
        except Exception as e:
            # Feed URLs contain a private token — never print them.
            print(f"WARNING: feed #{i + 1} failed to fetch/parse: {e}")
            continue
        print(f"feed #{i + 1}: parsed {len(list(cal.walk('VEVENT')))} events")
        for ev in cal.walk("VEVENT"):
            raw = str(ev.get("SUMMARY", "(untitled)"))
            tag = TAG_RE.search(raw)
            title = clean_title(TAG_RE.sub("", raw))
            # Class sessions (lectures, labs) come through as calendar-events;
            # real deadlines are assignment entries.
            uid = str(ev.get("UID", ""))
            kind = "class" if "-calendar-event-" in uid else "assignment"
            ctype = classify(title)
            if kind == "class" and ctype == "assignment":
                ctype = "class"
            course = match_course(" ".join(filter(None, [
                tag.group(1) if tag else "",
                " ".join(str(c) for c in (ev.get("CATEGORIES") or [])),
                raw,
            ])), courses)
            out.append(
                {
                    "title": title,
                    "start": to_iso(ev["DTSTART"].dt) if ev.get("DTSTART") else None,
                    "end": to_iso(ev["DTEND"].dt) if ev.get("DTEND") else None,
                    "course": course,
                    "type": ctype,
                    "source": "canvas",
                    "url": str(ev.get("URL")) if ev.get("URL") else None,
                    "location": str(ev.get("LOCATION")) if ev.get("LOCATION") else None,
                }
            )
    return out


def requests_get(url: str, binary: bool = False):
    import urllib.request

    url = url.strip().strip("'\"")
    if url and not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    return data if binary else data.decode("utf-8", "replace")


def clean_title(name: str) -> str:
    # Canvas prefixes some entries with the course code; strip common noise.
    return re.sub(r"\s+", " ", name).strip()


def manual_events(path: str, courses: dict) -> list[dict]:
    if not os.path.exists(path):
        return []
    data = yaml.safe_load(open(path)) or {}
    out = []
    for ev in data.get("events", []):
        title = ev["title"]
        start = ev.get("date") or ev.get("start")
        start = start.isoformat() if hasattr(start, "isoformat") else str(start)
        end = ev.get("end")
        end = end.isoformat() if hasattr(end, "isoformat") else end
        out.append(
            {
                "title": title,
                "start": start,
                "end": end,
                "course": match_course(str(ev.get("course", "")), courses),
                "type": ev.get("type") or classify(title),
                "source": "manual",
                "url": ev.get("url"),
                "location": ev.get("location"),
                "notes": ev.get("notes"),
            }
        )
    return out


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    courses = yaml.safe_load(open(os.path.join(here, "courses.yaml"))) or {}
    events = canvas_events(courses) + manual_events(os.path.join(here, "manual.yaml"), courses)
    seen, unique = set(), []
    for e in events:
        key = (e.get("title"), e.get("start"))
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda e: e.get("start") or "")
    events = unique
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "courses": courses,
        "events": events,
    }
    out = os.path.join(here, "events.json")
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {out}: {len(events)} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
