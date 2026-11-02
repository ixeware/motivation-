"""Picking sounds from TikTok.

Three routes, from zero-setup to official:

1. radar()     - no keys. Scans the latest videos of competitor accounts in the
                 niche (yt-dlp), groups them by sound and ranks the sounds by
                 views + freshness. "What sound is working in this niche now".
2. research()  - official TikTok Research API (client key/secret). Queries the
                 niche hashtags for the last N days and ranks music_id by views.
3. fetch()     - downloads the audio of any TikTok video (the sound you picked)
                 so the engine can align the climax to its drop.

Publishing tip: render the SFX-only version and add the chosen sound inside
the TikTok editor - the video is then attached to the sound page (more reach)
and is not muted for copyright.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "assets" / "music" / "tiktok"
DEFAULT_ACCOUNTS = ROOT / "config" / "competitors.txt"

GENERIC = {"original sound", "оригинальный звук", "son original", "sonido original", "som original",
           "audio originale", "oryginalny dźwięk", "originalton", "orijinal ses", "suara asli"}


@dataclass
class SoundStat:
    key: str
    title: str
    videos: int = 0
    views: int = 0
    score: float = 0.0
    best_url: str = ""
    best_views: int = 0
    accounts: set = field(default_factory=set)
    newest: int = 0

    def row(self):
        d = asdict(self)
        d["accounts"] = sorted(self.accounts)
        return d


def _ydl(opts=None):
    import yt_dlp
    base = {"quiet": True, "no_warnings": True, "skip_download": True, "noprogress": True}
    base.update(opts or {})
    return yt_dlp.YoutubeDL(base)


def read_accounts(path: str | Path | None = None) -> list[str]:
    p = Path(path) if path else DEFAULT_ACCOUNTS
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lstrip("@"))
    return out


def radar(accounts: list[str] | None = None, per_account: int = 30, *, include_generic: bool = False,
          verbose: bool = True) -> list[SoundStat]:
    """Rank sounds used by niche accounts. Score = sum(log10 views) weighted by freshness."""
    accounts = accounts or read_accounts()
    stats: dict[str, SoundStat] = {}
    now = time.time()
    for acc in accounts:
        url = f"https://www.tiktok.com/@{acc}"
        try:
            with _ydl({"extract_flat": True, "playlistend": per_account}) as y:
                info = y.extract_info(url, download=False)
        except Exception as e:  # noqa: BLE001
            if verbose:
                print(f"  ! {acc}: {e}")
            continue
        entries = info.get("entries") or []
        if verbose:
            print(f"  @{acc}: {len(entries)} videos")
        for e in entries:
            track = (e.get("track") or "").strip()
            if not track:
                continue
            generic = track.lower() in GENERIC
            if generic and not include_generic:
                continue
            key = track.lower()
            views = int(e.get("view_count") or 0)
            ts = int(e.get("timestamp") or 0)
            age_days = (now - ts) / 86400 if ts else 30
            fresh = math.exp(-age_days / 21)
            s = stats.setdefault(key, SoundStat(key=key, title=track))
            s.videos += 1
            s.views += views
            s.score += math.log10(views + 10) * (0.35 + fresh)
            s.accounts.add(acc)
            s.newest = max(s.newest, ts)
            if views > s.best_views:
                s.best_views, s.best_url = views, e.get("url") or e.get("webpage_url") or ""
    ranked = sorted(stats.values(), key=lambda s: s.score * (1 + 0.25 * (len(s.accounts) - 1)), reverse=True)
    return ranked


def fetch(url: str, out_dir: str | Path | None = None) -> dict:
    """Download the audio track of a TikTok video. Returns {'path', 'track', 'artist', ...}."""
    out_dir = Path(out_dir or CACHE)
    out_dir.mkdir(parents=True, exist_ok=True)
    with _ydl() as y:
        info = y.extract_info(url, download=False)
    vid = info.get("id")
    track = info.get("track") or "sound"
    safe = re.sub(r"[^\w\-]+", "_", f"{track}_{vid}")[:80]
    target = out_dir / f"{safe}.m4a"
    if not target.exists():
        opts = {"skip_download": False, "format": "bestaudio/best", "outtmpl": str(out_dir / f"{safe}.%(ext)s"),
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]}
        with _ydl(opts) as y:
            y.download([url])
    meta = {"path": str(target), "track": track, "artist": info.get("artist") or info.get("creator"),
            "source_url": info.get("webpage_url", url), "video_id": vid, "duration": info.get("duration")}
    (out_dir / f"{safe}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


# ----------------------------------------------------------------------------- official Research API

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
QUERY_URL = "https://open.tiktokapis.com/v2/research/video/query/"


def _token(client_key: str, client_secret: str) -> str:
    import requests
    r = requests.post(TOKEN_URL, data={"client_key": client_key, "client_secret": client_secret,
                                       "grant_type": "client_credentials"},
                      headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def research(hashtags: list[str], *, days: int = 14, region: str | None = None, pages: int = 5,
             client_key: str | None = None, client_secret: str | None = None) -> list[dict]:
    """Rank music_id in niche hashtags via the official TikTok Research API.

    Needs TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET of an approved Research API app.
    """
    import datetime as dt

    import requests
    ck = client_key or os.environ.get("TIKTOK_CLIENT_KEY")
    cs = client_secret or os.environ.get("TIKTOK_CLIENT_SECRET")
    if not ck or not cs:
        raise RuntimeError("Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET (TikTok Research API app).")
    tok = _token(ck, cs)
    end = dt.date.today()
    start = end - dt.timedelta(days=min(days, 30))
    cond = [{"operation": "IN", "field_name": "hashtag_name", "field_values": hashtags}]
    if region:
        cond.append({"operation": "EQ", "field_name": "region_code", "field_values": [region]})
    body = {"query": {"and": cond}, "start_date": start.strftime("%Y%m%d"), "end_date": end.strftime("%Y%m%d"),
            "max_count": 100}
    fields = "id,username,view_count,like_count,share_count,music_id,create_time,hashtag_names,video_description"
    agg: dict[str, dict] = defaultdict(lambda: {"videos": 0, "views": 0, "shares": 0, "example": None})
    for _ in range(pages):
        r = requests.post(f"{QUERY_URL}?fields={fields}", json=body,
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, timeout=60)
        r.raise_for_status()
        data = r.json().get("data", {})
        for v in data.get("videos", []):
            mid = str(v.get("music_id") or "")
            if not mid:
                continue
            a = agg[mid]
            a["videos"] += 1
            a["views"] += int(v.get("view_count") or 0)
            a["shares"] += int(v.get("share_count") or 0)
            if a["example"] is None or (v.get("view_count") or 0) > a["example"][1]:
                a["example"] = (f"https://www.tiktok.com/@{v.get('username')}/video/{v.get('id')}",
                                v.get("view_count") or 0)
        if not data.get("has_more"):
            break
        body["cursor"] = data.get("cursor")
        body["search_id"] = data.get("search_id")
    rows = []
    for mid, a in agg.items():
        score = a["videos"] * 2 + math.log10(a["views"] + 10) * 3 + math.log10(a["shares"] + 10)
        rows.append({"music_id": mid, "music_url": f"https://www.tiktok.com/music/-{mid}", "score": round(score, 2),
                     "videos": a["videos"], "views": a["views"], "example": a["example"][0] if a["example"] else ""})
    return sorted(rows, key=lambda r: r["score"], reverse=True)


# ----------------------------------------------------------------------------- local library


def library() -> list[dict]:
    """assets/music/library.json: [{"file": "...", "title": "...", "mood": ["dark","epic"], "drop": 12.3}]"""
    p = ROOT / "assets" / "music" / "library.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def pick_from_library(moods: list[str]) -> dict | None:
    best, score = None, -1
    for item in library():
        s = len(set(moods) & set(item.get("mood", [])))
        if s > score:
            best, score = item, s
    return best
