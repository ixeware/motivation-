"""Render a 3D short: python -m engine film <name> [--preview] [--still F[,F...]] [--finish-only]

Frames go to output/<slug>/frames[_preview]/f_0001.png and are reused when the run is restarted
(an interrupted render resumes where it stopped). Then post (bloom, impact frames, text) + sound.
"""
from __future__ import annotations

import importlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(name, *, preview=False, stills=None, step=1, f_from=None, f_to=None, samples=None, finish_only=False,
        log=print):
    mod = importlib.import_module(f".films.{name}", __package__)
    from . import post
    out = ROOT / "output" / mod.SLUG
    out.mkdir(parents=True, exist_ok=True)
    w, h = (360, 640) if preview else (1080, 1920)
    frames_dir = out / ("frames_preview" if preview else "frames")
    frames_dir.mkdir(exist_ok=True)
    all_frames = list(range(1, mod.N + 1))
    if not finish_only:
        import bpy
        film = mod.Film(w, h, samples or (4 if preview else 8))
        todo = stills or [f for f in all_frames[::step] if (f_from or 1) <= f <= (f_to or mod.N)]
        t0 = time.time()
        done = 0
        for f in todo:
            dst = frames_dir / f"f_{f:04d}.png"
            if dst.exists() and not stills:
                continue
            film.sc.frame_set(f)
            film.update(f)
            data = {"glows": film.glows(f) if hasattr(film, "glows") else []}
            if hasattr(film, "overlay"):
                data["ops"] = film.overlay(f)
            (frames_dir / f"f_{f:04d}.json").write_text(json.dumps(data))
            film.sc.render.filepath = str(dst)
            bpy.ops.render.render(write_still=True)
            done += 1
            if done % 10 == 0 or stills:
                el = time.time() - t0
                log(f"frame {f}  {done}/{len(todo)}  {el / done:.1f}s/frame  elapsed {el / 60:.1f} min")
        if stills:
            from PIL import Image
            paths = []
            for f in stills:
                img = Image.open(frames_dir / f"f_{f:04d}.png").convert("RGB")
                img = post.compose(img, f, frames_dir, mod.overlay_ops, getattr(mod, "IMPACT", {}), w / 1080)
                p = out / f"still_{f:04d}{'_preview' if preview else ''}.png"
                img.save(p)
                paths.append(str(p))
            return {"stills": paths}
    from ..audio.mix import write_wav
    wav = out / "soundtrack.wav"
    write_wav(wav, mod.soundtrack(music=True))
    wav_sfx = out / "soundtrack_sfx_only.wav"
    write_wav(wav_sfx, mod.soundtrack(music=False))
    have = [f for f in all_frames if (frames_dir / f"f_{f:04d}.png").exists()]
    suffix = "_preview" if preview else ""
    final = out / f"final{suffix}.mp4"
    post.finish(frames_dir, final, fps=mod.FPS, frames=all_frames if have else [], ops_fn=mod.overlay_ops,
                impacts=getattr(mod, "IMPACT", {}), audio=wav, size=(w, h), cover_frame=getattr(mod, "COVER_FRAME", None),
                cover_out=out / f"cover{suffix}.png")
    from ..audio.mix import mux
    sfx_only = out / f"final_sfx_only{suffix}.mp4"
    tmp = out / f"_video{suffix}.mp4"
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-an", "-c:v", "copy", str(tmp)], check=True)
    mux(tmp, wav_sfx, sfx_only)
    tmp.unlink(missing_ok=True)
    meta = getattr(mod, "META", {})
    cap = meta.get("caption", "") + "\n\n" + " ".join("#" + t for t in meta.get("hashtags", []))
    (out / "caption.txt").write_text(cap.strip() + "\n", encoding="utf-8")
    return {"video": str(final), "sfx_only": str(sfx_only), "cover": str(out / f"cover{suffix}.png"),
            "caption": str(out / "caption.txt"), "frames": len(have)}


if __name__ == "__main__":
    import sys
    print(json.dumps(run(sys.argv[1], preview="--preview" in sys.argv), indent=2))
