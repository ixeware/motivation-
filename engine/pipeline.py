"""One call: scenario -> music sync -> render -> mix -> final mp4 + caption."""
from __future__ import annotations

import copy
import json
import math
import shutil
import subprocess
from pathlib import Path

from .audio import bed as bedmod
from .audio import mix as mixmod
from .render.renderer import Renderer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"


def load(path_or_dict) -> tuple[dict, str]:
    if isinstance(path_or_dict, dict):
        sc = copy.deepcopy(path_or_dict)
        name = sc.get("meta", {}).get("slug", "video")
    else:
        p = Path(path_or_dict)
        sc = json.loads(p.read_text(encoding="utf-8"))
        name = sc.get("meta", {}).get("slug", p.stem)
    validate(sc)
    return sc, name


def validate(sc: dict):
    from .render import rig, vfx
    from .render.scenes import SCENES
    errs = []
    if not sc.get("shots"):
        errs.append("scenario has no shots")
    for i, sh in enumerate(sc.get("shots", [])):
        if sh.get("scene", "arena") not in SCENES:
            errs.append(f"shot {i}: unknown scene '{sh.get('scene')}' (have: {', '.join(SCENES)})")
        for aid, spec in (sh.get("actors") or {}).items():
            pose = (spec or {}).get("pose")
            if isinstance(pose, str) and pose not in rig.POSES:
                errs.append(f"shot {i}: actor {aid}: unknown pose '{pose}'")
        for ev in sh.get("events", []):
            if ev.get("do") == "pose" and isinstance(ev.get("pose"), str) and ev["pose"] not in rig.POSES:
                errs.append(f"shot {i}: event pose '{ev['pose']}' unknown")
            if ev.get("do") == "vfx" and ev.get("type") not in vfx.REGISTRY:
                errs.append(f"shot {i}: unknown vfx '{ev.get('type')}' (have: {', '.join(vfx.REGISTRY)})")
    if errs:
        raise ValueError("scenario errors:\n  " + "\n  ".join(errs))


def climax_time(sc: dict) -> float | None:
    T = 0.0
    for sh in sc["shots"]:
        if sh.get("climax"):
            return T + float(sh.get("climax_at", 0.0))
        T += float(sh.get("dur", 2.0))
    return None


def total_time(sc: dict) -> float:
    return sum(float(sh.get("dur", 2.0)) for sh in sc["shots"])


def resolve_music(sc: dict, *, verbose=True):
    """Returns (music_audio or None, beats_in_video_time, info)."""
    m = sc.get("music") or {"source": "synth"}
    src = m.get("source", "synth")
    snap = m.get("snap_cuts", True)
    climax = climax_time(sc)
    path = None
    info: dict = {"source": src}
    if src == "tiktok":
        from .music import tiktok
        meta = tiktok.fetch(m["url"])
        path = meta["path"]
        info.update(meta)
    elif src == "file":
        path = str((ROOT / m["file"]) if not Path(m["file"]).is_absolute() else m["file"])
        info["path"] = path
    elif src == "library":
        from .music import tiktok
        item = tiktok.pick_from_library(m.get("mood", ["dark", "epic"]))
        if item:
            path = str(ROOT / "assets" / "music" / item["file"])
            info.update(item)
        else:
            src = "synth"
    if path:
        an = mixmod.analyze(path)
        full = mixmod.load_audio(path)
        SR = mixmod.SR
        beat = 60.0 / max(an["tempo"], 40.0)
        drop = an["drop"]
        start = m.get("start")
        lead = 0.0
        if start is None:
            start = 0.0
            if climax is not None and drop is not None:
                if drop >= climax:
                    start = drop - climax
                else:
                    # drop comes too early: prepend whole bars of the intro and stretch the
                    # shots before the climax a little so the hit still lands on the drop
                    lead = math.ceil((climax - drop) / beat) * beat
                    _stretch_before_climax(sc, (drop + lead) / climax)
        start = float(start)
        seg = full[int(start * SR):]
        if lead > 0:
            seg = _xfade_concat(_take(full, 0.0, lead), seg)
        shift = lead - start
        beats = sorted({round(b + shift, 4) for b in an["beats"]} |
                       {round(b, 4) for b in an["beats"] if b < lead})
        if snap:
            fixed = climax_time(sc)
            mixmod.snap_shots(sc["shots"], beats)
            if fixed is not None:
                _stretch_before_climax(sc, fixed / (climax_time(sc) or fixed))
        total = total_time(sc)
        # loop from the drop if the track is shorter than the video
        loop_from = int((drop if drop is not None else 0.0) * SR)
        while len(seg) < int((total + 1.0) * SR) and len(full) - loop_from > SR:
            offset = (len(seg) - int(SR * 0.04)) / SR      # where the appended copy starts (video time)
            seg = _xfade_concat(seg, full[loop_from:])
            beats += [offset + b - loop_from / SR for b in an["beats"] if b >= loop_from / SR]
        audio = seg[: int((total + 1.0) * SR)]
        beats = sorted(b for b in beats if -0.5 <= b <= total + 1)
        info.update({"start": round(start, 2), "lead_in": round(lead, 2), "tempo": round(an["tempo"], 1),
                     "drop": drop})
        if verbose:
            print(f"music: {Path(path).name}  tempo={an['tempo']:.0f}  drop={drop}  start={start:.2f}s"
                  f"  lead-in={lead:.2f}s  climax={climax_time(sc)}")
        return audio, beats, info
    # procedural bed
    bpm = float(m.get("bpm", 100))
    beat = 60.0 / bpm
    drop = climax if climax is not None else total_time(sc) * 0.55
    grid = [drop + k * beat for k in range(-200, 200)]
    grid = [g for g in grid if 0 <= g <= total_time(sc) + 1]
    if snap:
        mixmod.snap_shots(sc["shots"], grid)
    total = total_time(sc)
    drop = climax_time(sc) or total * 0.55
    audio, beats = bedmod.make_bed(total + 1.0, drop, bpm)
    info.update({"bpm": bpm, "drop": round(drop, 2)})
    if verbose:
        print(f"music: procedural bed {bpm:.0f} BPM, drop at {drop:.2f}s")
    return audio, beats, info


def _take(x, t0: float, t1: float):
    SR = mixmod.SR
    return x[int(t0 * SR):int(t1 * SR)]


def _xfade_concat(a, b, ms: float = 40.0):
    import numpy as np
    n = int(mixmod.SR * ms / 1000)
    if len(a) < n or len(b) < n:
        return np.concatenate([a, b])
    ramp = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    mid = a[-n:] * (1 - ramp) + b[:n] * ramp
    return np.concatenate([a[:-n], mid, b[n:]])


def _stretch_before_climax(sc: dict, k: float):
    """Scale durations of the shots before the climax shot (and the climax offset) by k."""
    if abs(k - 1.0) < 1e-4:
        return
    for sh in sc["shots"]:
        if sh.get("climax"):
            sh["climax_at"] = round(float(sh.get("climax_at", 0.0)) * k, 4)
            break
        sh["dur"] = round(float(sh.get("dur", 2.0)) * k, 4)


def produce(scenario, *, out_dir: str | Path | None = None, scale: float = 1.0, crf: int = 18,
            verbose: bool = True) -> dict:
    sc, name = load(scenario)
    out = Path(out_dir) if out_dir else OUTPUT / name
    out.mkdir(parents=True, exist_ok=True)
    music, beats, minfo = resolve_music(sc, verbose=verbose)
    sc["_beats"] = beats
    r = Renderer(sc, scale=scale)
    if verbose:
        print(f"render: {name}  {r.total:.1f}s  {r.w}x{r.h}@{r.fps}")
    silent = out / "video_silent.mp4"
    r.render(silent, crf=crf)
    m = sc.get("music") or {}
    full = mixmod.mix(r.total, r.cues, music=music, music_gain=float(m.get("gain", 0.75)))
    sfx_only = mixmod.mix(r.total, r.cues, music=None)
    mixmod.write_wav(out / "audio_full.wav", full)
    mixmod.write_wav(out / "audio_sfx.wav", sfx_only)
    final = out / "final.mp4"
    final_sfx = out / "final_sfx_only.mp4"
    mixmod.mux(silent, out / "audio_full.wav", final)
    mixmod.mux(silent, out / "audio_sfx.wav", final_sfx)
    clim = climax_time(sc)
    cover_t = min(r.total - 0.1, (clim + 0.35) if clim is not None else r.total * 0.6)
    r.still(cover_t, out / "cover.png")
    _contact_sheet(final, out / "contact_sheet.jpg", r.total)
    caption = _caption(sc, minfo)
    (out / "caption.txt").write_text(caption, encoding="utf-8")
    (out / "scenario.resolved.json").write_text(json.dumps({k: v for k, v in sc.items() if k != "_beats"},
                                                           ensure_ascii=False, indent=2), encoding="utf-8")
    for f in (silent, out / "audio_full.wav", out / "audio_sfx.wav"):
        f.unlink(missing_ok=True)
    if verbose:
        print(f"done -> {final}")
    return {"final": str(final), "final_sfx_only": str(final_sfx), "cover": str(out / "cover.png"),
            "contact_sheet": str(out / "contact_sheet.jpg"), "caption": str(out / "caption.txt"), "music": minfo}


def _contact_sheet(video: Path, out: Path, total: float):
    ff = shutil.which("ffmpeg") or "ffmpeg"
    fps = 12 / max(total, 1)
    subprocess.run([ff, "-y", "-v", "error", "-i", str(video), "-vf", f"fps={fps:.4f},scale=270:-1,tile=6x2",
                    "-frames:v", "1", str(out)], check=False)


def _caption(sc: dict, minfo: dict) -> str:
    meta = sc.get("meta", {})
    tags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    lines = [meta.get("caption", ""), "", tags, ""]
    m = sc.get("music") or {}
    if minfo.get("source") == "synth":
        lines.append("SOUND: procedural bed is baked in final.mp4. For reach: upload final_sfx_only.mp4 and add a")
        lines.append("trending sound in the TikTok editor (see `python -m engine music radar`).")
        if m.get("suggest"):
            lines.append(f"Suggested sound: {m['suggest']}")
    else:
        lines.append(f"SOUND: {minfo.get('track') or minfo.get('path')}  start at {minfo.get('start', 0)}s")
        if minfo.get("source_url"):
            lines.append(f"Sound source: {minfo['source_url']}")
        lines.append("Upload final_sfx_only.mp4 and pick this sound in the TikTok editor, trimmed to the start above.")
    clim = climax_time(sc)
    if clim is not None:
        lines.append(f"Climax (sync to the drop) at {clim:.2f}s")
    return "\n".join(lines).strip() + "\n"
