"""Command line.

  python -m engine make "эго против таланта, отсылка на пурпурный"   # one request -> video
  python -m engine render scenarios/talent_vs_hardwork_purple.json   # scenario -> video
  python -m engine render scenarios/x.json --preview                 # fast half-res draft
  python -m engine still scenarios/x.json 12.5                       # one frame (png)
  python -m engine music radar                                       # niche sound radar (no keys)
  python -m engine music fetch <tiktok_url>                          # download a sound
  python -m engine music research motivation discipline              # official Research API
  python -m engine music strip edit.mp4 --ours output/x/final.mp4    # clean song out of a TikTok edit
  python -m engine music grid assets/music/user/song.wav             # exact beat grid + phrase starts
  python -m engine refs | poses | scenes                             # catalogs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _cmd_render(a):
    from .pipeline import produce
    res = produce(a.scenario, out_dir=a.out, scale=0.5 if a.preview else a.scale, crf=26 if a.preview else a.crf)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def _cmd_still(a):
    from .pipeline import load
    from .render.renderer import Renderer
    sc, name = load(a.scenario)
    r = Renderer(sc, scale=a.scale)
    out = Path(a.out or ROOT / "output" / name / f"still_{a.t:06.2f}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    r.still(a.t, out)
    print(out)


def _cmd_make(a):
    from .planner import plan
    sc = plan(a.request, use_llm=not a.no_llm, lang=a.lang)
    slug = sc["meta"]["slug"]
    p = ROOT / "scenarios" / f"{slug}.json"
    p.write_text(json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"scenario -> {p}")
    if a.music_url:
        sc["music"] = {"source": "tiktok", "url": a.music_url, "snap_cuts": True}
        p.write_text(json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")
    if not a.plan_only:
        from .pipeline import produce
        res = produce(p, scale=0.5 if a.preview else 1.0, crf=26 if a.preview else 18)
        print(json.dumps(res, ensure_ascii=False, indent=2))


def _cmd_music(a):
    from .music import tiktok
    if a.action == "radar":
        accounts = a.args or None
        rows = tiktok.radar(accounts, per_account=a.limit, include_generic=a.generic)
        print(f"\n{'#':>2}  {'score':>6}  {'videos':>6}  {'views':>11}  sound  /  best example")
        for i, s in enumerate(rows[: a.top], 1):
            print(f"{i:>2}  {s.score:6.1f}  {s.videos:6d}  {s.views:11,d}  {s.title}  /  {s.best_url}")
        if a.json:
            Path(a.json).write_text(json.dumps([s.row() for s in rows], ensure_ascii=False, indent=2), encoding="utf-8")
    elif a.action == "fetch":
        for url in a.args:
            print(json.dumps(tiktok.fetch(url), ensure_ascii=False, indent=2))
    elif a.action == "research":
        rows = tiktok.research(a.args or ["motivation", "discipline", "mindset"], days=a.days, region=a.region)
        for i, r in enumerate(rows[: a.top], 1):
            print(f"{i:>2}  {r['score']:6.1f}  {r['videos']:4d}  {r['views']:11,d}  {r['music_url']}  {r['example']}")
    elif a.action == "analyze":
        from .audio.mix import analyze
        for p in a.args:
            print(p, json.dumps({k: v for k, v in analyze(p).items() if k != "beats"}))
    elif a.action == "strip":
        from .music.strip import strip
        if not a.args or not a.ours:
            raise SystemExit("usage: music strip <tiktok_edit.mp4> --ours output/<slug>/final.mp4 [--out file.wav]")
        out = a.out or str(ROOT / "assets" / "music" / "user" / (Path(a.args[0]).stem + "_clean.wav"))
        print(json.dumps(strip(a.args[0], a.ours, out), ensure_ascii=False, indent=2))
    elif a.action == "grid":
        from .music.strip import grid
        for p in a.args:
            g = grid(p)
            print(p)
            print(f"  bpm {g['bpm']}  beat {g['period']} s  first beat {g['t0']} s")
            print(f"  phrase starts (4 bars): {g['phrases']}")
            print(f"  bar starts: {g['bars']}")


def _cmd_catalog(a):
    if a.cmd == "refs":
        from .references import REFERENCES
        for r in REFERENCES:
            print(f"- {r['id']:<15} [{r['vfx']}]  {r['visual']}")
            print(f"  {'':15} смысл: {r['meaning']}")
    elif a.cmd == "poses":
        from .render.rig import POSES
        for k, v in POSES.items():
            print(f"{k:<16} {v.get('view')}")
    elif a.cmd == "scenes":
        from .render.scenes import SCENES
        for k, v in SCENES.items():
            print(f"{k:<10} {(v.__doc__ or '').strip().splitlines()[0] if v.__doc__ else ''}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render")
    r.add_argument("scenario")
    r.add_argument("--out")
    r.add_argument("--preview", action="store_true")
    r.add_argument("--scale", type=float, default=1.0)
    r.add_argument("--crf", type=int, default=18)
    r.set_defaults(fn=_cmd_render)

    s = sub.add_parser("still")
    s.add_argument("scenario")
    s.add_argument("t", type=float)
    s.add_argument("--out")
    s.add_argument("--scale", type=float, default=1.0)
    s.set_defaults(fn=_cmd_still)

    m = sub.add_parser("make")
    m.add_argument("request")
    m.add_argument("--no-llm", action="store_true", help="rule-based planner only")
    m.add_argument("--plan-only", action="store_true", help="write the scenario, do not render")
    m.add_argument("--preview", action="store_true")
    m.add_argument("--music-url", help="TikTok video URL whose sound to use")
    m.add_argument("--lang", default="en", help="language of ALL on-screen text and the caption (default: en)")
    m.set_defaults(fn=_cmd_make)

    mu = sub.add_parser("music")
    mu.add_argument("action", choices=["radar", "fetch", "research", "analyze", "strip", "grid"])
    mu.add_argument("args", nargs="*")
    mu.add_argument("--limit", type=int, default=30)
    mu.add_argument("--top", type=int, default=15)
    mu.add_argument("--days", type=int, default=14)
    mu.add_argument("--region")
    mu.add_argument("--generic", action="store_true", help="include 'original sound' entries")
    mu.add_argument("--json")
    mu.add_argument("--ours", help="strip: our original render (its audio is removed from the edit)")
    mu.add_argument("--out", help="strip: output wav")
    mu.set_defaults(fn=_cmd_music)

    for name in ("refs", "poses", "scenes"):
        c = sub.add_parser(name)
        c.set_defaults(fn=_cmd_catalog)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
