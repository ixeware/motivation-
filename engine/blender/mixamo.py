"""Download Mixamo animations (FBX, without skin) with YOUR OWN Mixamo session.

Mixamo has no public API; this uses the same endpoints as the mixamo.com web app, with the access
token of your logged-in session (DevTools console on mixamo.com: `localStorage.access_token`).
The token lives about a day. It is read from the MIXAMO_TOKEN env var or from a file given by
MIXAMO_TOKEN_FILE / --token-file, never stored in the repo, never printed.

Mixamo assets may be used in your own videos but must not be redistributed, so clips land in the
gitignored assets/mocap/cache/.

  python -m engine mocap search "sitting"
  python -m engine mocap fetch "Typing" "Sitting Laughing" --token-file ~/.mixamo_token
  python -m engine mocap fetch "Sitting Angry|Highly"          # name|part of the description
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.mixamo.com/api/v1"
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "assets" / "mocap" / "cache"


# short name -> (fetch spec "Name|description words", file stem in the cache)
LIBRARY = {
    "idle": ("Sitting Idle|Still In A Chair", "sitting_idle_sitting_still_in_a_chair"),
    "typing": ("Typing|Sitting At A Computer", "typing_sitting_at_a_computer_and_typing"),
    "laugh": ("Sitting Laughing|While Laughing", "sitting_laughing_sitting_while_laughing"),
    "disbelief": ("Sitting Disbelief|Hands On Head", "sitting_disbelief_sitting_disbelief_with_hands_on_head"),
    "slump": ("Sitting Disbelief|Head Forward", "sitting_disbelief_sitting_in_disbelief_with_head_forward"),
    "angry": ("Sitting Angry|Highly Aggravated", "sitting_angry_sitting_highly_aggravated"),
    "victory": ("Sitting Victory|Celebrating Victory", "sitting_victory_celebrating_victory_while_sitting"),
    "thumbs": ("Sitting Thumbs Up|Giving Thumbs Up", "sitting_thumbs_up_giving_thumbs_up_while_sitting"),
    "writing": ("Writing|Male Writing While Seated", "writing_male_writing_while_seated"),
    "drink": ("Sitting Drinking|Canned Beverage", "sitting_drinking_having_a_seat_and_drinking_a_canned_beverag"),
}


class MixamoError(RuntimeError):
    pass


def _token(token_file: str | None = None) -> str | None:
    if token_file:
        return Path(token_file).expanduser().read_text().strip()
    if os.environ.get("MIXAMO_TOKEN"):
        return os.environ["MIXAMO_TOKEN"].strip()
    if os.environ.get("MIXAMO_TOKEN_FILE"):
        return Path(os.environ["MIXAMO_TOKEN_FILE"]).expanduser().read_text().strip()
    return None


class Client:
    def __init__(self, token: str | None = None):
        self.token = token

    def _req(self, method, path, body=None, auth=True):
        url = path if path.startswith("http") else API + path
        data = json.dumps(body).encode() if body is not None else None
        rq = urllib.request.Request(url, data=data, method=method)
        rq.add_header("X-Api-Key", "mixamo2")
        rq.add_header("Accept", "application/json")
        if data is not None:
            rq.add_header("Content-Type", "application/json")
        if auth:
            if not self.token:
                raise MixamoError("no Mixamo token: set MIXAMO_TOKEN or pass --token-file")
            rq.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            if e.code in (401, 403):
                raise MixamoError(f"Mixamo said {e.code}: the token is missing or expired (log in again, copy a new one)") from None
            raise MixamoError(f"{method} {url.split('?')[0]} -> {e.code}: {msg}") from None
        return json.loads(raw) if raw else {}

    # --- catalog (works without a token) ---------------------------------------------------
    def search(self, query, limit=96, kind="Motion"):
        q = urllib.parse.urlencode({"page": 1, "limit": limit, "order": "", "type": kind, "query": query})
        return self._req("GET", f"/products?{q}", auth=False).get("results", [])

    def find(self, spec):
        """'Name' or 'Name|description words' -> the best matching catalog entry."""
        name, _, desc = spec.partition("|")
        name, desc = name.strip(), desc.strip().lower()
        res = self.search(name)
        exact = [r for r in res if r.get("name", "").lower() == name.lower()]
        pool = exact or res
        if desc:
            words = desc.split()
            pool = [r for r in pool if all(w in (r.get("description") or "").lower() for w in words)] or pool
        if not pool:
            raise MixamoError(f"nothing on Mixamo matches {spec!r}")
        return pool[0]

    # --- account side (needs the token) ------------------------------------------------------
    def primary_character(self):
        r = self._req("GET", "/characters/primary")
        return r.get("primary_character_id"), r.get("primary_character_name")

    def export(self, product, character_id, fps=30):
        detail = self._req("GET", f"/products/{product['id']}?similar=0&character_id={character_id}")
        gms = dict(detail["details"]["gms_hash"])
        params = gms.get("params") or []
        gms["params"] = ",".join(str(p[1]) for p in params) if isinstance(params, list) else params
        body = {"character_id": character_id, "gms_hash": [gms],
                "preferences": {"format": "fbx7", "skin": "false", "fps": str(fps), "reducekf": "0"},
                "product_name": detail.get("description") or product.get("description") or product["name"],
                "type": detail.get("type", "Motion")}
        self._req("POST", "/animations/export", body)
        t0 = time.time()
        while time.time() - t0 < 180:
            time.sleep(2.0)
            m = self._req("GET", f"/characters/{character_id}/monitor")
            st = m.get("status")
            if st == "completed":
                return m["job_result"]
            if st == "failed":
                raise MixamoError(f"export failed: {m.get('message')}")
        raise MixamoError("export timed out")


def slug(product) -> str:
    base = f"{product['name']} {product.get('description') or ''}".lower()
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")[:60]


def fetch(specs, *, token_file=None, out_dir=CACHE, fps=30, pause=1.5) -> list[dict]:
    """Download each clip spec ('Name' or 'Name|description words') as FBX without skin."""
    cl = Client(_token(token_file))
    cid, cname = cl.primary_character()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for spec in specs:
        p = cl.find(spec)
        dst = out_dir / f"{slug(p)}.fbx"
        if dst.exists() and dst.stat().st_size > 1000:
            done.append({"spec": spec, "file": str(dst), "cached": True})
            continue
        url = cl.export(p, cid, fps=fps)
        with urllib.request.urlopen(url, timeout=120) as r:
            dst.write_bytes(r.read())
        done.append({"spec": spec, "name": p["name"], "description": p.get("description"), "file": str(dst),
                     "character": cname, "kb": dst.stat().st_size // 1024})
        time.sleep(pause)
    return done
