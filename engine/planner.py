"""One request -> scenario.

  plan("эго против таланта и дисциплины, отсылка на пурпурный")

Step 1 (brief): Claude (if credentials are available) or the keyword rules turn
the request into a small brief: template, hero, rivals, hidden reference,
texts. Step 2 (build): a deterministic builder expands the brief into a full,
valid scenario, so the render never breaks on a creative answer.
"""
from __future__ import annotations

import json
import re
import time

from . import references as refs

TEMPLATES = {
    "classroom_rematch": "reference format: 3 archetypes at desks, hero gets a bad grade, night grind montage, "
                         "rematch where the hidden reference fires, hero gets A+",
    "duel_power": "two archetypes fight, an omen grows behind them, the hero is revealed and ends the fight with "
                  "the hidden reference",
    "grind_levelup": "solo grind as a game: quest window, night study, training, LEVEL UP and an army of shadows",
    "adaptation": "hero keeps getting hit by an obstacle, a wheel above the head turns each time, then he adapts and "
                  "counters",
    "towers": "newer reference look: black stage, spotlights, glossy reflective floor; three archetypes stack glowing "
              "blocks into towers, two of them quit, the hero keeps stacking; the finished tower shoots a beam of light "
              "and the hidden reference fires",
}

ARCHETYPES = [  # (regex on the lowercased request, english label, core color)
    (r"\bэго|\bego\b", "EGO", "violet"), (r"гордост|гордын|pride", "PRIDE", "violet"),
    (r"талант|talent", "TALENT", "gold"), (r"дисциплин|discipline", "DISCIPLINE", "cyan"),
    (r"хардворк|hard ?work|трудолюб|\bтруд", "HARD WORK", "ice"), (r"\bлен[ьи]|ленив|lazy|laziness", "LAZINESS", "#9ca3af"),
    (r"страх|fear", "FEAR", "#f87171"), (r"сомнен|doubt", "DOUBT", "#94a3b8"),
    (r"мотивац|motivation", "MOTIVATION", "#fb923c"), (r"фокус|focus", "FOCUS", "green"),
    (r"терпен|patience", "PATIENCE", "#2dd4bf"), (r"привычк|habit", "HABIT", "green"),
    (r"комфорт|comfort", "COMFORT", "#f9a8d4"), (r"завист|envy", "ENVY", "#a3e635"),
    (r"уверенн|confidence", "CONFIDENCE", "gold"), (r"ярост|злост|гнев|rage", "RAGE", "red"),
    (r"неудач|провал|failure", "FAILURE", "#9ca3af"), (r"прокрастин|procrastination", "PROCRASTINATION", "#9ca3af"),
    (r"\bя\b|\bты\b|\byou\b", "YOU", "white"),
]
NEGATIVE = {"LAZINESS", "FEAR", "DOUBT", "FAILURE", "PROCRASTINATION", "COMFORT", "ENVY"}
CORE_OF = {lbl: c for _, lbl, c in ARCHETYPES}

QUOTES = {
    "ru": {
        "classroom_rematch": (["ИНОГДА ГОРДОСТЬ —", "ЛУЧШЕЕ ТОПЛИВО.*"], "СДЕЛАЙ ЕЁ СИЛОЙ, А НЕ СЛАБОСТЬЮ",
                              "Иногда гордость — лучшее топливо. Сделай её силой, а не слабостью."),
        "duel_power": (["ОНИ СПОРИЛИ, КТО СИЛЬНЕЕ.", "А {hero} ПРОСТО НЕ УМЕЕТ ПРОИГРЫВАТЬ.*"], "НЕ СПОРЬ. СТРЕЛЯЙ.",
                       "Пока одни спорят, кто сильнее, другие просто не умеют проигрывать."),
        "grind_levelup": (["НИКТО НЕ ВИДЕЛ НОЧЕЙ.", "ВСЕ УВИДЕЛИ УРОВЕНЬ.*"], "ЕЖЕДНЕВНЫЙ КВЕСТ НЕ ЗАКРОЕТСЯ САМ",
                          "Никто не видел ночей. Все увидели уровень."),
        "adaptation": (["КАЖДОЕ ПАДЕНИЕ —", "ЭТО ПОВОРОТ КОЛЕСА.*"], "ТЫ НЕ ПРОИГРЫВАЕШЬ. ТЫ АДАПТИРУЕШЬСЯ",
                       "Каждое падение — это поворот колеса. Ты не проигрываешь, ты адаптируешься."),
        "towers": (["МОТИВАЦИЯ — ЭТО ИСКРА.", "ДИСЦИПЛИНА — ЭТО АРМИЯ.*"], "КАЖДЫЙ ДЕНЬ ВСТАЁТ ЗА ТВОЕЙ СПИНОЙ",
                   "Мотивация — это искра. Дисциплина — это армия. Каждый день, когда ты всё равно пришёл, "
                   "однажды встанет за твоей спиной."),
    },
    "en": {
        "classroom_rematch": (["SOMETIMES PRIDE", "IS THE BEST FUEL.*"], "MAKE IT A STRENGTH, NOT A WEAKNESS",
                              "Sometimes your pride is the best fuel. Make it a strength, not a weakness."),
        "duel_power": (["THEY ARGUED WHO WAS STRONGER.", "{hero} REFUSED TO LOSE.*"], "DON'T ARGUE. FIRE.",
                       "While they argue who is stronger, some people simply refuse to lose."),
        "grind_levelup": (["NOBODY SAW THE NIGHTS.", "EVERYONE SAW THE LEVEL.*"], "THE DAILY QUEST WON'T CLEAR ITSELF",
                          "Nobody saw the nights. Everyone saw the level."),
        "adaptation": (["EVERY FALL IS", "ONE TURN OF THE WHEEL.*"], "YOU ARE NOT LOSING. YOU ARE ADAPTING",
                       "Every fall is one turn of the wheel. You are not losing, you are adapting."),
        "towers": (["MOTIVATION IS A SPARK.", "DISCIPLINE IS AN ARMY.*"], "EVERY DAY YOU SHOWED UP STANDS BEHIND YOU",
                   "Motivation is a spark. Discipline is an army."),
    },
}

HASHTAGS = ["motivation", "mindset", "discipline", "selfimprovement", "grind", "fyp"]


# ============================================================================ brief


def rule_brief(request: str, lang: str = "ru") -> dict:
    t = request.lower()
    found: list[tuple[int, str, str]] = []
    for pat, label, core in ARCHETYPES:
        m = re.search(pat, t)
        if m and label not in [f[1] for f in found]:
            found.append((m.start(), label, core))
    found.sort()
    labels = [f[1] for f in found]
    ref = refs.match(t)
    if re.search(r"башн|строит|постро|складыва|блок|кирпич|сцен|прожектор|отражени", t):
        template = "towers"
    elif re.search(r"класс|оценк|экзамен|школ|контрольн|тест|урок", t):
        template = "classroom_rematch"
    elif re.search(r"адапт|колес|снова и снова|раз за разом", t):
        template = "adaptation"
    elif re.search(r"уровен|левел|систем|квест|прокач", t):
        template = "grind_levelup"
    elif re.search(r"дерут|драк|бой|битв|борют|сраж|дуэл|\bvs\b|против", t):
        template = "duel_power"
    else:
        template = {"system": "grind_levelup", "shadow_rise": "grind_levelup", "wheel": "adaptation",
                    "hollow_purple": "duel_power", "aura": "duel_power", "domain_shrine": "duel_power"}.get(
            ref or "", "classroom_rematch")
    if ref == "wheel" and template != "towers":
        template = "adaptation"
    if ref is None:
        ref = {"classroom_rematch": "domain_void", "duel_power": "hollow_purple", "grind_levelup": "system",
               "adaptation": "wheel", "towers": "shadow_rise"}[template]
    positive = [lbl for lbl in labels if lbl not in NEGATIVE]
    default_hero = {"classroom_rematch": "EGO", "duel_power": "EGO", "grind_levelup": "DISCIPLINE",
                    "adaptation": "YOU", "towers": "DISCIPLINE"}[template]
    if template == "towers":
        hero = "DISCIPLINE" if "DISCIPLINE" in positive else (positive[-1] if positive else default_hero)
    elif "EGO" in positive:
        hero = "EGO"
    elif template == "duel_power" and len(positive) >= 3:
        hero = positive[-1]
    elif template == "duel_power" and len(positive) == 2 and not [x for x in labels if x in NEGATIVE]:
        hero = default_hero  # the two named ones fight, the hero is the third
    elif positive:
        hero = positive[-1] if template != "duel_power" else positive[0]
    else:
        hero = default_hero
    rivals = [lbl for lbl in labels if lbl != hero]
    rivals.sort(key=lambda x: x not in NEGATIVE if template in ("adaptation", "grind_levelup") else 0)
    defaults = {"classroom_rematch": ["DISCIPLINE", "TALENT"], "duel_power": ["TALENT", "HARD WORK"],
                "grind_levelup": ["LAZINESS", "DOUBT"], "adaptation": ["FAILURE", "FEAR"],
                "towers": ["TALENT", "MOTIVATION"]}[template]
    for d in defaults:
        if len(rivals) >= 2:
            break
        if d not in rivals and d != hero:
            rivals.append(d)
    lines, sub, caption = QUOTES.get(lang, QUOTES["en"])[template]
    hero_word = hero if lang == "en" else {"EGO": "ЭГО", "DISCIPLINE": "ДИСЦИПЛИНА", "FOCUS": "ФОКУС",
                                           "PRIDE": "ГОРДОСТЬ", "HARD WORK": "ТРУД"}.get(hero, hero)
    lines = [ln.replace("{hero}", hero_word) for ln in lines]
    return {"template": template, "reference": ref, "hero": hero, "rivals": rivals[:2],
            "hook": "" if template == "towers" else " VS ".join(rivals[:2] + [hero])
            if template in ("classroom_rematch", "duel_power")
            else f"{hero}: DAY 1" if template == "grind_levelup" else f"{hero} VS {rivals[0]}",
            "end_lines": lines, "end_sub": sub, "caption": caption, "hashtags": HASHTAGS + [hero.lower().replace(" ", "")],
            "lang": lang}


BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "template": {"type": "string", "enum": list(TEMPLATES)},
        "reference": {"type": "string", "enum": [r["id"] for r in refs.REFERENCES]},
        "hero": {"type": "string"},
        "rivals": {"type": "array", "items": {"type": "string"}},
        "hook": {"type": "string"},
        "end_lines": {"type": "array", "items": {"type": "string"}},
        "end_sub": {"type": "string"},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["template", "reference", "hero", "rivals", "hook", "end_lines", "end_sub", "caption", "hashtags"],
    "additionalProperties": False,
}


def llm_brief(request: str, lang: str = "ru") -> dict:
    """Ask Claude for the creative brief (structured JSON output)."""
    import anthropic

    ref_lines = "\n".join(f"- {r['id']}: {r['visual']} | meaning: {r['meaning']}" for r in refs.REFERENCES)
    tpl_lines = "\n".join(f"- {k}: {v}" for k, v in TEMPLATES.items())
    system = f"""You plan 15-25 second vertical motivational TikTok videos in one fixed visual style:
minimal white pill-shaped stick figures in a dark room, each labelled with an English uppercase archetype
(EGO, TALENT, DISCIPLINE, HARD WORK, FEAR, LAZINESS, FOCUS...), a glowing chest core per archetype, red grade
stamps, night-grind montages, and ONE hidden anime/film power move per video.

Templates:
{tpl_lines}

Hidden references (pick the one that best serves the request and the message):
{ref_lines}

Rules:
- The reference is shown, never named: no anime titles, character names, technique names or quotes in hook,
  end_lines, end_sub, caption or hashtags.
- hero and rivals are short English uppercase archetype labels; exactly two rivals.
- hook: <= 34 characters, English uppercase, e.g. "TALENT VS DISCIPLINE VS EGO".
- end_lines: 1-3 short uppercase lines in language '{lang}' that land the message; mark the single most
  important word by appending '*' to it (it is painted in the accent color).
- end_sub: one short uppercase line in '{lang}'. caption: 1-2 sentences in '{lang}', no hashtags inside.
- hashtags: 5-8 lowercase words without '#', niche + broad (motivation, mindset, discipline...)."""
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": BRIEF_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": f"Request: {request}"}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model declined the request")
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    brief = json.loads(text)
    brief["lang"] = lang
    return brief


def _sanitize(brief: dict) -> dict:
    b = dict(brief)
    if b.get("template") not in TEMPLATES:
        b["template"] = "classroom_rematch"
    if refs.by_id(b.get("reference", "")) is None:
        b["reference"] = "domain_void"
    b["hero"] = (b.get("hero") or "EGO").upper()[:14]
    rv = [r.upper()[:14] for r in b.get("rivals", []) if r and r.upper() != b["hero"]]
    for d in ("TALENT", "DISCIPLINE", "HARD WORK"):
        if len(rv) >= 2:
            break
        if d not in rv and d != b["hero"]:
            rv.append(d)
    b["rivals"] = rv[:2]
    b["end_lines"] = [ln for ln in b.get("end_lines", []) if ln][:3] or ["KEEP GOING.*"]
    return b


# ============================================================================ build helpers


def _core(label: str, default="white"):
    return CORE_OF.get(label, default)


def _title(b, accent, dur=3.2):
    return {"scene": "title", "dur": dur, "out": "fade",
            "params": {"lines": b["end_lines"], "sub": b.get("end_sub", ""), "accent": accent,
                       "size": 92 if max(len(x) for x in b["end_lines"]) > 16 else 104}}


def _power_classroom(ref: dict, hero="hero", rivals=("r1", "r2")) -> tuple[list, dict]:
    """Events for the rematch moment in the classroom + extra actor overrides."""
    rid = ref["id"]
    ev: list = []
    if rid.startswith("domain"):
        ev += [{"t": 0.55, "do": "pose", "who": hero, "pose": "cast_sit", "dur": 0.25},
               {"t": 0.6, "do": "vfx", "type": "domain", "caster": hero, "style": ref.get("params", {}).get("style", "void"),
                "expand_at": 0.35, "dur": 2.8, "frozen": list(rivals)}]
    elif rid == "hollow_purple":
        ev += [{"t": 0.4, "do": "pose", "who": hero, "pose": "cast_sit", "dur": 0.25},
               {"t": 0.4, "do": "vfx", "type": "hollow_purple", "caster": hero, "charge": 0.5, "merge": 0.45,
                "travel": 0.8, "r": 40, "big": 160, "dur": 2.8, "to": [1.3, -0.3]}]
    elif rid == "aura":
        ev += [{"t": 0.7, "do": "vfx", "type": "aura", "caster": hero, "targets": list(rivals)}]
    elif rid == "black_flash":
        ev += [{"t": 0.55, "do": "pose", "who": hero, "pose": "fist_up", "dur": 0.15},
               {"t": 0.85, "do": "pose", "who": hero, "pose": "sit", "dur": 0.08},
               {"t": 0.93, "do": "vfx", "type": "black_flash", "at": {"who": hero, "at": "hand_r"}}]
    elif rid == "system":
        ev += [{"t": 0.7, "do": "vfx", "type": "system", "title": "NOTIFICATION",
                "lines": ["Quest: [Pass the exam] complete", {"text": "Level {}", "count": [1, 2], "color": "#fde68a"}],
                "y": 0.28, "dur": 2.4}]
    elif rid == "wheel":
        ev += [{"t": 0.0, "do": "vfx", "type": "wheel", "who": hero, "turns": [0.8], "dur": 3.0, "scale": 0.8}]
    elif rid == "curse_marks":
        ev += [{"t": 0.6, "do": "marks", "who": hero, "to": 1.0, "dur": 0.4}, {"t": 0.62, "do": "impact", "frames": 2}]
    elif rid == "blindfold":
        ev += [{"t": 0.6, "do": "band", "who": hero, "to": 0.0, "dur": 0.4},
               {"t": 0.7, "do": "eyes", "who": hero, "to": 1.0, "dur": 0.3}, {"t": 0.7, "do": "impact", "frames": 2}]
    elif rid == "afterimage":
        ev += [{"t": 0.5, "do": "vfx", "type": "speedlines", "dur": 1.0, "a": 0.4}]
    return ev, {}


# ============================================================================ templates


def build_classroom(b: dict) -> dict:
    ref = refs.by_id(b["reference"])
    hero, (r1, r2) = b["hero"], b["rivals"]
    sleeper = "r2" if r2 == "TALENT" else ("r1" if r1 == "TALENT" else None)
    band = 1.0 if ref["id"] in ("blindfold",) else 0.0
    def seat_pose(aid):
        return "sleep" if aid == sleeper else "sit"
    actors0 = {"r1": {"pose": seat_pose("r1"), "zzz": sleeper == "r1"},
               "hero": {"pose": "sit", "level": 0.15, "band": band},
               "r2": {"pose": seat_pose("r2"), "zzz": sleeper == "r2"}}
    s1_ev = [{"t": 0.7, "do": "sheet", "who": "r1", "mark": "A"},
             {"t": 1.3, "do": "sheet", "who": "r2", "mark": "A-"},
             {"t": 2.15, "do": "sheet", "who": "hero", "mark": "C"},
             {"t": 2.45, "do": "pose", "who": "hero", "pose": "head_in_hands", "dur": 0.3},
             {"t": 2.45, "do": "core", "who": "hero", "to": 0.35, "dur": 0.6}]
    if ref["id"] == "curse_marks":
        s1_ev.append({"t": 2.7, "do": "marks", "who": "hero", "to": 0.35, "dur": 0.3})
    if ref["id"] == "wheel":
        s1_ev.append({"t": 2.2, "do": "vfx", "type": "wheel", "who": "hero", "turns": [0.3], "dur": 1.2,
                      "scale": 0.8})
    shots = [
        {"scene": "classroom", "dur": 3.4, "params": {"walker": {"from": -0.2, "to": 1.25, "t0": 0.0, "t1": 2.6}},
         "camera": {"from": {"zoom": 1.0, "x": -30}, "to": {"zoom": 1.09, "x": 20}},
         "actors": actors0, "events": s1_ev},
        {"scene": "closeup", "dur": 2.3, "camera": {"from": {"zoom": 1.0}, "to": {"zoom": 1.12, "y": -30}, "dof": 1.6},
         "actors": {"hero": {"pose": "head_in_hands", "sheet": "C", "level": 0.15, "core": 0.35, "band": band,
                             "marks": 0.35 if ref["id"] == "curse_marks" else 0.0}},
         "events": [{"t": 0.3, "do": "pose", "who": "hero", "pose": "slumped", "dur": 1.2, "ease": "sine"},
                    {"t": 1.3, "do": "core", "who": "hero", "to": 1.4, "dur": 0.6},
                    {"t": 1.35, "do": "punch", "amp": 0.05, "sfx": "hit", "gain": 0.4}]},
        {"scene": "study", "dur": 4.4, "params": {"hours": [23.0, 30.5], "books": [1, 8]},
         "camera": {"from": {"zoom": 1.0}, "to": {"zoom": 1.07}},
         "actors": {"hero": {"pose": "write", "mods": {"writing": 1}, "level": 0.15, "core": 1.2}},
         "events": [{"t": 0.2, "do": "level", "who": "hero", "to": 0.85, "dur": 4.0, "ease": "linear"}]},
        {"scene": "board", "dur": 2.6, "camera": {"from": {"zoom": 1.04}, "to": {"zoom": 1.12, "x": 60}},
         "actors": {"hero": {"pose": "board_write", "mods": {"board": 1}, "level": 0.85}}},
    ]
    if ref["id"] == "afterimage":
        shots[2]["events"].append({"t": 1.2, "do": "vfx", "type": "afterimage", "who": "hero", "dur": 2.4})
    if ref["id"] == "system":
        shots[2]["events"].append({"t": 0.6, "do": "vfx", "type": "system", "title": "DAILY QUEST",
                                   "lines": [{"text": "Practice problems  {}/100", "count": [0, 100]},
                                             "Penalty for skipping: weakness"], "y": 0.22, "dur": 3.4})
    power_ev, _ = _power_classroom(ref)
    rematch_ev = [{"t": 0.15, "do": "sheet", "who": "r1", "mark": "A"},
                  {"t": 0.3, "do": "sheet", "who": "r2", "mark": "A-"}] + power_ev + [
        {"t": 1.75, "do": "sheet", "who": "hero", "mark": "A+"},
        {"t": 2.0, "do": "pose", "who": "hero", "pose": "arms_up", "dur": 0.3},
        {"t": 2.0, "do": "level", "who": "hero", "to": 1.0, "dur": 0.6, "text": "MAX"}]
    shots.append({"scene": "classroom", "dur": 3.4, "climax": True, "climax_at": 0.95, "in": "flash",
                  "params": {"sky": "dawn", "extras": 1},
                  "camera": {"from": {"zoom": 1.05, "x": 0}, "to": {"zoom": 1.16, "y": -20}},
                  "actors": {"r1": {"pose": seat_pose("r1"), "zzz": sleeper == "r1"},
                             "hero": {"pose": "sit", "level": 0.85, "core": 1.4, "band": band,
                                      "marks": 1.0 if ref["id"] == "curse_marks" else 0.0},
                             "r2": {"pose": seat_pose("r2"), "zzz": sleeper == "r2"}},
                  "events": rematch_ev})
    shots.append({"scene": "closeup", "dur": 2.2, "params": {"sky": "dawn"},
                  "camera": {"from": {"zoom": 1.1}, "to": {"zoom": 1.0}, "dof": 1.5},
                  "actors": {"hero": {"pose": "arms_up", "sheet": "A+", "level": 1.0, "level_text": "MAX",
                                      "core": 1.6, "eyes": 1.0 if ref["id"] in ("blindfold", "domain_void") else 0,
                                      "marks": 1.0 if ref["id"] == "curse_marks" else 0.0}}})
    shots.append(_title(b, ref["color"] if ref["id"] != "curse_marks" else _core(hero, "violet")))
    cast = {"r1": {"label": r1, "core": _core(r1, "cyan")}, "r2": {"label": r2, "core": _core(r2, "gold")},
            "hero": {"label": hero, "core": _core(hero, "violet"), "eyes": "#7dd3fc"}}
    return _wrap(b, cast, shots, ref)


def _omen(ref: dict) -> dict:
    return {"t": 0.0, "do": "vfx", "type": "energy_orb", "at": [0.5, 0.9], "r": 115, "grow": 2.6, "dur": 3.0,
            "layer": "back", "color": ref["color"] if ref["id"] != "black_flash" else "#7f1d1d"}


def _fight(t0: float, a="r1", b="r2", heavy=False) -> list:
    ev = [{"t": t0, "do": "pose", "who": a, "pose": "punch", "dur": 0.12, "ease": "out"},
          {"t": t0 + 0.07, "do": "pose", "who": b, "pose": "guard", "dur": 0.1},
          {"t": t0 + 0.1, "do": "shake", "amp": 0.45, "dur": 0.25, "sfx": "hit", "gain": 0.7},
          {"t": t0 + 0.4, "do": "pose", "who": a, "pose": "stance", "dur": 0.25},
          {"t": t0 + 0.8, "do": "pose", "who": b, "pose": "punch", "dur": 0.12, "ease": "out"},
          {"t": t0 + 0.86, "do": "pose", "who": a, "pose": "hit", "dur": 0.12},
          {"t": t0 + 1.25, "do": "pose", "who": b, "pose": "stance", "dur": 0.25},
          {"t": t0 + 1.3, "do": "pose", "who": a, "pose": "stance", "dur": 0.3}]
    if heavy:
        ev.append({"t": t0 + 0.9, "do": "vfx", "type": "black_flash", "at": {"who": b, "at": "hand_r"},
                   "targets": [a]})
    else:
        ev.append({"t": t0 + 0.9, "do": "impact", "frames": 2, "sfx": "hit"})
    return ev


def build_duel(b: dict) -> dict:
    ref = refs.by_id(b["reference"])
    if ref["id"] in ("system",):
        return build_grind(b)
    if ref["id"] == "wheel":
        return build_adaptation(b)
    hero, (r1, r2) = b["hero"], b["rivals"]
    fighters = lambda: {"r1": {"x": 0.32, "pose": "stance", "facing": 1, "s": 82, "mods": {"fight": 1}},
                        "r2": {"x": 0.68, "pose": "stance", "facing": -1, "s": 82, "mods": {"fight": 1}}}
    band = 1.0 if ref["id"] in ("hollow_purple", "domain_void", "blindfold") else 0.0
    shots = [
        {"scene": "arena", "dur": 3.3, "params": {"spot": 0.7},
         "camera": {"from": {"zoom": 1.3, "y": 40}, "to": {"zoom": 1.15, "y": 20}},
         "actors": fighters(), "events": _fight(0.5, heavy=True) + [
            {"t": 2.6, "do": "pose", "who": "r1", "pose": "kick", "dur": 0.14, "ease": "out"},
            {"t": 2.68, "do": "pose", "who": "r2", "pose": "guard", "dur": 0.1},
            {"t": 2.72, "do": "shake", "amp": 0.6, "dur": 0.3, "sfx": "hit"},
            {"t": 3.0, "do": "pose", "who": "r1", "pose": "stance", "dur": 0.25}]},
        {"scene": "arena", "dur": 3.0, "params": {"spot": 0.5},
         "camera": {"from": {"zoom": 1.0, "y": 60}, "to": {"zoom": 0.9, "y": 140}},
         "actors": fighters(), "events": [_omen(ref)] + _fight(0.5)},
        {"scene": "void", "dur": 2.4, "params": {"spot": 0.35, "spot_c": ref["color"], "tint": "#120a1f"},
         "camera": {"from": {"on": "hero", "zoom": 1.9, "y": -140}, "to": {"on": "hero", "zoom": 1.55, "y": -60},
                    "dof": 1.4},
         "actors": {"hero": {"x": 0.5, "pose": "stand", "band": band, "s": 92, "mods": {"float": 1}}},
         "events": [{"t": 0.35, "do": "band", "who": "hero", "to": 0.0, "dur": 0.5, "ease": "out"},
                    {"t": 0.4, "do": "eyes", "who": "hero", "to": 1.0 if band else 0.0, "dur": 0.4},
                    {"t": 0.5, "do": "glitch", "who": "hero", "dur": 0.4}]},
    ]
    climax_actors = {"r1": {"x": 0.32, "pose": "stance", "facing": 1, "s": 82},
                     "r2": {"x": 0.68, "pose": "stance", "facing": -1, "s": 82}}
    rid = ref["id"]
    if rid == "hollow_purple":
        shots[2]["events"] += [{"t": 1.0, "do": "pose", "who": "hero", "pose": "hands_out", "dur": 0.5},
                               {"t": 1.0, "do": "vfx", "type": "hollow_purple", "caster": "hero", "charge": 1.4,
                                "merge": 1.1, "travel": 0.9, "r": 50, "dur": 2.5,
                                "from": {"who": "hero", "at": "core", "dy": -1.6}}]
        shots.append({"scene": "void", "dur": 1.1, "params": {"spot": 0.35, "spot_c": ref["color"], "tint": "#120a1f"},
                      "camera": {"from": {"on": "hero", "zoom": 1.25, "y": -40}, "to": {"on": "hero", "zoom": 1.45,
                                                                                         "y": -80}},
                      "actors": {"hero": {"x": 0.5, "pose": "hands_out", "eyes": 1.0, "s": 92, "mods": {"float": 1}}},
                      "events": [{"t": 0.0, "do": "vfx", "type": "hollow_purple", "caster": "hero", "offset": 1.4,
                                  "charge": 1.4, "merge": 1.1, "travel": 0.9, "r": 50, "dur": 2.5,
                                  "from": {"who": "hero", "at": "core", "dy": -1.6}},
                                 {"t": 0.15, "do": "pose", "who": "hero", "pose": "hands_together", "dur": 0.35},
                                 {"t": 0.8, "do": "pose", "who": "hero", "pose": "cast", "dur": 0.25}]})
        shots.append({"scene": "arena", "dur": 2.8, "climax": True, "climax_at": 0.0, "in": "impact",
                      "params": {"spot": 0.5}, "camera": {"from": {"zoom": 0.92, "y": 120}, "to": {"zoom": 1.0, "y": 60}},
                      "actors": climax_actors,
                      "events": [{"t": 0.0, "do": "pose", "who": "r1", "pose": "guard", "dur": 0.15},
                                 {"t": 0.0, "do": "pose", "who": "r2", "pose": "guard", "dur": 0.15},
                                 {"t": 0.0, "do": "vfx", "type": "hollow_purple", "offset": 2.5, "charge": 1.4,
                                  "merge": 1.1, "travel": 1.0, "r": 64, "big": 210, "dur": 6.0, "from": [1.15, 0.95],
                                  "to": [-0.3, 0.55], "length": 2400, "targets": ["r1", "r2"]}]})
    else:
        shots[2]["events"].append({"t": 1.2, "do": "pose", "who": "hero", "pose": "cast", "dur": 0.3})
        trio = {"r1": {"x": 0.2, "pose": "stand", "s": 70}, "hero": {"x": 0.5, "pose": "cast", "s": 86, "eyes": 1.0},
                "r2": {"x": 0.8, "pose": "stand", "s": 70}}
        ev: list = []
        if rid.startswith("domain"):
            ev = [{"t": 0.0, "do": "vfx", "type": "domain", "caster": "hero", "expand_at": 0.3, "dur": 3.4,
                   "style": ref.get("params", {}).get("style", "void"), "frozen": ["r1", "r2"]}]
        elif rid == "aura":
            ev = [{"t": 0.2, "do": "vfx", "type": "aura", "caster": "hero", "targets": ["r1", "r2"]}]
        elif rid == "shadow_rise":
            ev = [{"t": 0.0, "do": "vfx", "type": "shadow_rise", "caster": "hero", "count": 6, "dur": 3.6},
                  {"t": 1.6, "do": "fade", "who": "r1", "to": 0.15, "dur": 0.8},
                  {"t": 1.6, "do": "fade", "who": "r2", "to": 0.15, "dur": 0.8}]
        elif rid == "black_flash":
            trio["hero"]["pose"] = "stand"
            ev = [{"t": 0.25, "do": "pose", "who": "hero", "pose": "fire_left", "dur": 0.1},
                  {"t": 0.32, "do": "vfx", "type": "black_flash", "at": {"who": "hero", "at": "hand_l"},
                   "targets": ["r1"]},
                  {"t": 0.4, "do": "fade", "who": "r1", "to": 0.1, "dur": 0.5},
                  {"t": 1.1, "do": "pose", "who": "hero", "pose": "fire_right", "dur": 0.1},
                  {"t": 1.17, "do": "vfx", "type": "black_flash", "at": {"who": "hero", "at": "hand_r"},
                   "targets": ["r2"]},
                  {"t": 1.25, "do": "fade", "who": "r2", "to": 0.1, "dur": 0.5}]
        elif rid == "afterimage":
            trio["hero"].update({"x": 0.14, "pose": "stand"})
            ev = [{"t": 0.1, "do": "vfx", "type": "afterimage", "who": "hero", "dur": 1.8, "count": 7},
                  {"t": 0.2, "do": "move", "who": "hero", "x": 0.86, "dur": 0.7, "ease": "inout_cubic"},
                  {"t": 0.95, "do": "pose", "who": "r1", "pose": "slumped", "dur": 0.2},
                  {"t": 1.0, "do": "pose", "who": "r2", "pose": "slumped", "dur": 0.2},
                  {"t": 1.0, "do": "impact", "frames": 2}]
        elif rid == "curse_marks":
            ev = [{"t": 0.2, "do": "marks", "who": "hero", "to": 1.0, "dur": 0.3},
                  {"t": 0.3, "do": "vfx", "type": "aura", "caster": "hero", "targets": ["r1", "r2"]}]
        else:  # blindfold
            ev = [{"t": 0.2, "do": "vfx", "type": "aura", "caster": "hero", "targets": ["r1", "r2"]}]
        shots.append({"scene": "void", "dur": 3.6, "climax": True, "climax_at": 0.3, "in": "flash",
                      "params": {"spot": 0.5, "spot_c": ref["color"], "tint": "#0f0a18"},
                      "camera": {"from": {"zoom": 0.95, "y": 40}, "to": {"zoom": 1.05, "y": 0}},
                      "actors": trio, "events": ev})
    shots.append({"scene": "void", "dur": 2.4, "params": {"spot": 0.6, "spot_c": ref["color"], "tint": "#0f0a18"},
                  "camera": {"from": {"on": "hero", "zoom": 1.0, "y": 40}, "to": {"on": "hero", "zoom": 1.12}},
                  "actors": {"hero": {"x": 0.5, "pose": "cast", "eyes": 1.0 if band else 0.0, "s": 86, "level": 0.15,
                                      "marks": 1.0 if rid == "curse_marks" else 0.0}},
                  "events": [{"t": 0.3, "do": "pose", "who": "hero", "pose": "stand", "dur": 0.6},
                             {"t": 0.4, "do": "level", "who": "hero", "to": 1.0, "dur": 1.3, "ease": "out_cubic",
                              "text": "MAX"},
                             {"t": 0.9, "do": "eyes", "who": "hero", "to": 0.0, "dur": 0.8},
                             {"t": 0.9, "do": "band", "who": "hero", "to": band, "dur": 0.6}]})
    shots.append(_title(b, ref["color"]))
    cast = {"r1": {"label": r1, "core": _core(r1, "gold")}, "r2": {"label": r2, "core": _core(r2, "cyan")},
            "hero": {"label": hero, "core": _core(hero, "violet"), "eyes": "#7dd3fc"}}
    return _wrap(b, cast, shots, ref)


def build_grind(b: dict) -> dict:
    ref = refs.by_id(b["reference"])
    hero = b["hero"]
    shots = [
        {"scene": "study", "dur": 3.0, "params": {"hours": [22.0, 23.5], "books": [0, 1], "dawn": False},
         "camera": {"from": {"zoom": 1.15}, "to": {"zoom": 1.05}},
         "actors": {"hero": {"pose": "sit_side", "level": 0.0, "level_text": "LV 1"}},
         "events": [{"t": 0.3, "do": "vfx", "type": "system", "title": "NOTIFICATION",
                     "lines": ["Daily quest has arrived.", "Fail = stay the same."], "y": 0.24, "dur": 2.5},
                    {"t": 1.9, "do": "pose", "who": "hero", "pose": "write", "dur": 0.4, "mods": {"writing": 1}}]},
        {"scene": "study", "dur": 4.2, "params": {"hours": [23.5, 30.5], "books": [1, 9]},
         "camera": {"from": {"zoom": 1.0}, "to": {"zoom": 1.08}},
         "actors": {"hero": {"pose": "write", "mods": {"writing": 1}, "level": 0.0, "level_text": "LV 1"}},
         "events": [{"t": 0.1, "do": "level", "who": "hero", "to": 0.9, "dur": 3.9, "ease": "linear"},
                    {"t": 0.4, "do": "vfx", "type": "system", "title": "DAILY QUEST",
                     "lines": [{"text": "Focus hours   {}/8", "count": [0, 8]},
                               {"text": "Problems      {}/100", "count": [0, 100]}], "y": 0.2, "dur": 3.5}]},
        {"scene": "board", "dur": 2.4, "camera": {"from": {"zoom": 1.04}, "to": {"zoom": 1.12, "x": 60}},
         "actors": {"hero": {"pose": "board_write", "mods": {"board": 1}, "level": 0.9}}},
        {"scene": "arena", "dur": 2.6, "params": {"spot": 0.6},
         "camera": {"from": {"zoom": 1.35, "y": 40}, "to": {"zoom": 1.2}},
         "actors": {"hero": {"x": 0.5, "pose": "stance", "facing": 1, "s": 82, "mods": {"fight": 1}, "level": 0.9}},
         "events": [{"t": 0.3, "do": "pose", "who": "hero", "pose": "punch", "dur": 0.1},
                    {"t": 0.36, "do": "shake", "amp": 0.3, "dur": 0.2, "sfx": "hit", "gain": 0.5},
                    {"t": 0.6, "do": "pose", "who": "hero", "pose": "stance", "dur": 0.2},
                    {"t": 0.9, "do": "pose", "who": "hero", "pose": "punch_back", "dur": 0.1},
                    {"t": 0.96, "do": "shake", "amp": 0.3, "dur": 0.2, "sfx": "hit", "gain": 0.5},
                    {"t": 1.2, "do": "pose", "who": "hero", "pose": "stance", "dur": 0.2},
                    {"t": 1.6, "do": "pose", "who": "hero", "pose": "kick", "dur": 0.12},
                    {"t": 1.66, "do": "impact", "frames": 2, "sfx": "hit"},
                    {"t": 2.1, "do": "pose", "who": "hero", "pose": "stance", "dur": 0.2}]},
    ]
    climax_ev = [{"t": 0.2, "do": "vfx", "type": "system", "title": "LEVEL UP",
                  "lines": [{"text": "Level  {}", "count": [1, 2], "color": "#fde68a"},
                            "New skill unlocked: Consistency"], "y": 0.2, "dur": 2.6},
                 {"t": 0.2, "do": "level", "who": "hero", "to": 1.0, "dur": 0.5, "text": "LV 2"},
                 {"t": 0.3, "do": "eyes", "who": "hero", "to": 1.0, "dur": 0.3}]
    if ref["id"] in ("shadow_rise", "system"):
        climax_ev.append({"t": 0.9, "do": "vfx", "type": "shadow_rise", "caster": "hero", "count": 6, "dur": 3.2})
    elif ref["id"].startswith("domain"):
        climax_ev.append({"t": 0.8, "do": "vfx", "type": "domain", "caster": "hero", "expand_at": 0.3, "dur": 2.8,
                          "style": ref.get("params", {}).get("style", "void")})
    elif ref["id"] == "hollow_purple":
        climax_ev += [{"t": 0.6, "do": "pose", "who": "hero", "pose": "hands_out", "dur": 0.3},
                      {"t": 0.6, "do": "vfx", "type": "hollow_purple", "caster": "hero", "charge": 0.8, "merge": 0.6,
                       "travel": 0.8, "r": 42, "big": 180, "dur": 3.0, "to": [1.3, 0.1]}]
    else:
        climax_ev.append({"t": 0.8, "do": "vfx", "type": "aura", "caster": "hero"})
    shots.append({"scene": "void", "dur": 4.0, "climax": True, "climax_at": 0.2, "in": "flash",
                  "params": {"spot": 0.55, "spot_c": "#7c3aed", "tint": "#0d0a18"},
                  "camera": {"from": {"on": "hero", "zoom": 1.15, "y": 80}, "to": {"on": "hero", "zoom": 1.0, "y": 120}},
                  "actors": {"hero": {"x": 0.5, "pose": "stand", "s": 84, "level": 0.9, "level_text": "LV 1"}},
                  "events": climax_ev})
    shots.append(_title(b, ref["color"]))
    cast = {"hero": {"label": hero, "core": _core(hero, "cyan"), "eyes": "#a78bfa"}}
    return _wrap(b, cast, shots, ref)


def build_adaptation(b: dict) -> dict:
    ref = refs.by_id("wheel") if b["reference"] not in ("wheel",) else refs.by_id(b["reference"])
    hero, rival = b["hero"], b["rivals"][0]
    duo = lambda: {"hero": {"x": 0.34, "pose": "stance", "facing": 1, "s": 80, "mods": {"fight": 1}},
                   "foe": {"x": 0.68, "pose": "stance", "facing": -1, "s": 88, "mods": {"fight": 1}}}

    def beaten(t0):
        return [{"t": t0, "do": "pose", "who": "foe", "pose": "punch", "dur": 0.12, "ease": "out"},
                {"t": t0 + 0.06, "do": "pose", "who": "hero", "pose": "hit", "dur": 0.12},
                {"t": t0 + 0.08, "do": "impact", "frames": 2, "sfx": "hit"},
                {"t": t0 + 0.1, "do": "shake", "amp": 0.6, "dur": 0.3},
                {"t": t0 + 0.5, "do": "pose", "who": "foe", "pose": "stance", "dur": 0.25},
                {"t": t0 + 0.7, "do": "pose", "who": "hero", "pose": "stance", "dur": 0.4}]
    shots = [
        {"scene": "arena", "dur": 3.0, "params": {"spot": 0.6},
         "camera": {"from": {"zoom": 1.3, "y": 30}, "to": {"zoom": 1.2}},
         "actors": duo(),
         "events": beaten(0.6) + [{"t": 0.0, "do": "vfx", "type": "wheel", "who": "hero", "turns": [1.4],
                                   "dur": 3.0, "scale": 0.85}]},
        {"scene": "arena", "dur": 2.6, "params": {"spot": 0.6},
         "camera": {"from": {"zoom": 1.15, "x": -40}, "to": {"zoom": 1.25, "x": 0}},
         "actors": duo(),
         "events": beaten(0.4) + [{"t": 0.0, "do": "vfx", "type": "wheel", "who": "hero", "turns": [1.1],
                                   "dur": 2.6, "scale": 0.85, "offset": 0.4},
                                  {"t": 1.4, "do": "text", "text": "ADAPTING...", "pos": "top", "dur": 1.1,
                                   "size": 44, "color": "#e8d18a"}]},
        {"scene": "study", "dur": 3.0, "params": {"hours": [23, 29], "books": [2, 7]},
         "camera": {"from": {"zoom": 1.0}, "to": {"zoom": 1.06}},
         "actors": {"hero": {"pose": "write", "mods": {"writing": 1}, "level": 0.2}},
         "events": [{"t": 0.1, "do": "level", "who": "hero", "to": 0.8, "dur": 2.8},
                    {"t": 0.0, "do": "vfx", "type": "wheel", "who": "hero", "turns": [1.6], "dur": 3.0,
                     "scale": 0.7, "offset": 0.4}]},
        {"scene": "arena", "dur": 3.4, "climax": True, "climax_at": 1.1, "params": {"spot": 0.7},
         "camera": {"from": {"zoom": 1.25}, "to": {"zoom": 1.1, "y": 20}},
         "actors": duo(),
         "events": [{"t": 0.0, "do": "vfx", "type": "wheel", "who": "hero", "turns": [0.6], "dur": 3.4,
                     "scale": 0.85, "offset": 0.4},
                    {"t": 0.5, "do": "pose", "who": "foe", "pose": "punch", "dur": 0.12, "ease": "out"},
                    {"t": 0.55, "do": "pose", "who": "hero", "pose": "guard", "dur": 0.1},
                    {"t": 0.6, "do": "shake", "amp": 0.3, "dur": 0.2, "sfx": "clank"},
                    {"t": 1.0, "do": "pose", "who": "hero", "pose": "punch", "dur": 0.1, "ease": "out"},
                    {"t": 1.1, "do": "vfx", "type": "black_flash", "at": {"who": "hero", "at": "hand_r"},
                     "targets": ["foe"]},
                    {"t": 1.15, "do": "pose", "who": "foe", "pose": "hit", "dur": 0.15},
                    {"t": 1.3, "do": "fade", "who": "foe", "to": 0.0, "dur": 0.9},
                    {"t": 1.8, "do": "pose", "who": "hero", "pose": "stance", "dur": 0.4}]},
        {"scene": "void", "dur": 2.2, "params": {"spot": 0.6, "spot_c": "#e8d18a"},
         "camera": {"from": {"on": "hero", "zoom": 1.0, "y": 60}, "to": {"on": "hero", "zoom": 1.1, "y": 40}},
         "actors": {"hero": {"x": 0.5, "pose": "stand", "s": 86, "level": 0.8}},
         "events": [{"t": 0.0, "do": "vfx", "type": "wheel", "who": "hero", "turns": [], "dur": 2.2, "offset": 0.5},
                    {"t": 0.3, "do": "level", "who": "hero", "to": 1.0, "dur": 0.8, "text": "ADAPTED"}]},
        _title(b, ref["color"]),
    ]
    cast = {"hero": {"label": hero, "core": _core(hero, "cyan")}, "foe": {"label": rival, "core": _core(rival, "red")}}
    return _wrap(b, cast, shots, ref)


SUBS = {
    "ru": {"intro": "ОДНА ЦЕЛЬ. ТРИ ПОДХОДА.", "quit": "{r} РЕШИЛ,\nЧТО ЭТОГО ХВАТИТ.",
           "burn": "{r} ГОРИТ ЯРКО.\nНО НЕДОЛГО.", "keep": "{h}\nПРОСТО ПРОДОЛЖАЕТ.", "days": "ДЕНЬ ЗА ДНЁМ."},
    "en": {"intro": "ONE GOAL. THREE WAYS.", "quit": "{r} DECIDED\nIT WAS ENOUGH.",
           "burn": "{r} BURNS BRIGHT.\nBUT NOT FOR LONG.", "keep": "{h}\nJUST KEEPS GOING.", "days": "DAY AFTER DAY."},
}
RU_WORD = {"TALENT": "ТАЛАНТ", "MOTIVATION": "МОТИВАЦИЯ", "DISCIPLINE": "ДИСЦИПЛИНА", "EGO": "ЭГО",
           "HARD WORK": "ТРУД", "FOCUS": "ФОКУС", "LAZINESS": "ЛЕНЬ", "FEAR": "СТРАХ", "DOUBT": "СОМНЕНИЕ",
           "PRIDE": "ГОРДОСТЬ", "HABIT": "ПРИВЫЧКА", "PATIENCE": "ТЕРПЕНИЕ", "COMFORT": "КОМФОРТ", "YOU": "ТЫ"}


def build_towers(b: dict) -> dict:
    """Stage + spotlights + glossy floor. r1 quits early (sparkle), r2 burns out (flame), hero keeps stacking."""
    ref = refs.by_id(b["reference"])
    hero, (r1, r2) = b["hero"], b["rivals"]
    lang = b.get("lang", "ru")
    sub = SUBS.get(lang, SUBS["en"])
    word = (lambda x: RU_WORD.get(x, x)) if lang == "ru" else (lambda x: x)
    stage = lambda s, floor=None: {"s": s, **({"floor": floor} if floor else {})}
    shots = [
        {"scene": "stage", "dur": 4.2, "params": stage(30),
         "camera": {"from": {"zoom": 1.0, "y": 50}, "to": {"zoom": 1.07, "y": 10}},
         "actors": {"r1": {"x": 0.2, "tower": {"base": 0}}, "r2": {"x": 0.5, "tower": {"base": 0}},
                    "hero": {"x": 0.8, "tower": {"base": 0}, "level": 0.05}},
         "events": [{"t": 0.3, "do": "text", "text": sub["intro"], "dur": 3.6},
                    {"t": 0.3, "do": "stack", "who": "r1", "until": 4.2, "rate": 2.3},
                    {"t": 0.3, "do": "stack", "who": "r2", "until": 4.2, "rate": 2.4},
                    {"t": 0.3, "do": "stack", "who": "hero", "until": 4.2, "rate": 1.0},
                    {"t": 0.3, "do": "level", "who": "hero", "to": 0.2, "dur": 3.8, "ease": "linear"},
                    {"t": 1.2, "do": "sparkle", "who": "r1", "to": 1.0, "dur": 0.2, "hold": 1.4}]},
        {"scene": "stage", "dur": 3.2, "params": stage(58, 1450),
         "camera": {"from": {"zoom": 1.0, "y": 20}, "to": {"zoom": 1.08, "y": -10}, "dof": 1.2},
         "actors": {"r1": {"x": 0.42, "tower": {"base": 9}}},
         "events": [{"t": 0.0, "do": "stack", "who": "r1", "until": 0.95, "rate": 2.3},
                    {"t": 0.3, "do": "text", "text": sub["quit"].format(r=word(r1)), "dur": 2.8},
                    {"t": 1.0, "do": "pose", "who": "r1", "pose": "squat_rest", "dur": 0.45, "ease": "out_cubic"},
                    {"t": 1.4, "do": "sparkle", "who": "r1", "to": 1.0, "dur": 0.15, "hold": 1.1},
                    {"t": 2.2, "do": "dim", "who": "r1", "to": 0.85, "dur": 0.9},
                    {"t": 2.2, "do": "spot", "who": "r1", "to": 0.35, "dur": 0.9}]},
        {"scene": "stage", "dur": 3.4, "params": stage(58, 1450),
         "camera": {"from": {"zoom": 1.06, "y": -10}, "to": {"zoom": 1.0, "y": 20}, "dof": 1.2},
         "actors": {"r2": {"x": 0.42, "tower": {"base": 9}, "flame": 1.0}},
         "events": [{"t": 0.0, "do": "stack", "who": "r2", "until": 1.45, "rate": 2.6},
                    {"t": 0.3, "do": "text", "text": sub["burn"].format(r=word(r2)), "dur": 3.0},
                    {"t": 0.9, "do": "flame", "who": "r2", "to": 0.0, "dur": 1.5, "ease": "inout"},
                    {"t": 1.5, "do": "pose", "who": "r2", "pose": "squat_despair", "dur": 0.4, "ease": "out_cubic"},
                    {"t": 2.3, "do": "pose", "who": "r2", "pose": "squat_slump", "dur": 0.6},
                    {"t": 2.1, "do": "dim", "who": "r2", "to": 1.0, "dur": 1.0},
                    {"t": 2.1, "do": "spot", "who": "r2", "to": 0.3, "dur": 1.0}]},
        {"scene": "stage", "dur": 3.4, "params": stage(62, 1450),
         "camera": {"from": {"zoom": 1.0, "y": 10}, "to": {"zoom": 1.1, "y": -60}, "dof": 1.2},
         "actors": {"hero": {"x": 0.42, "tower": {"base": 7}, "level": 0.3}},
         "events": [{"t": 0.0, "do": "stack", "who": "hero", "until": 3.4, "rate": 1.2},
                    {"t": 0.3, "do": "text", "text": sub["keep"].format(h=word(hero)), "dur": 3.0},
                    {"t": 0.2, "do": "level", "who": "hero", "to": 0.6, "dur": 3.0, "ease": "linear"}]},
        {"scene": "stage", "dur": 2.8, "params": stage(30),
         "camera": {"from": {"zoom": 1.08, "y": 10}, "to": {"zoom": 0.98, "y": -40}},
         "actors": {"r1": {"x": 0.2, "tower": {"base": 11}, "pose": "squat_rest", "dim": 0.85, "spot": 0.3},
                    "r2": {"x": 0.5, "tower": {"base": 12}, "pose": "squat_slump", "dim": 1.0, "spot": 0.25,
                           "flame": 0.0},
                    "hero": {"x": 0.8, "tower": {"base": 11}, "level": 0.6}},
         "events": [{"t": 0.0, "do": "stack", "who": "hero", "until": 2.8, "rate": 3.0},
                    {"t": 0.2, "do": "text", "text": sub["days"], "dur": 2.4},
                    {"t": 0.0, "do": "level", "who": "hero", "to": 0.95, "dur": 2.8, "ease": "linear"},
                    {"t": 1.4, "do": "spot", "who": "r1", "to": 0.1, "dur": 1.0},
                    {"t": 1.4, "do": "spot", "who": "r2", "to": 0.08, "dur": 1.0}]},
    ]
    climax_ev = [{"t": 0.0, "do": "stack", "who": "hero", "until": 0.5, "rate": 2.0},
                 {"t": 0.45, "do": "vfx", "type": "light_pillar", "at": {"who": "hero", "at": "tower"}, "floor": 1400,
                  "width": 70, "dur": 3.4},
                 {"t": 0.45, "do": "impact", "frames": 3},
                 {"t": 0.55, "do": "level", "who": "hero", "to": 1.0, "dur": 0.4, "text": "MAX"},
                 {"t": 0.9, "do": "pose", "who": "hero", "pose": "stand_proud", "dur": 0.5, "ease": "out_cubic"},
                 {"t": 1.0, "do": "eyes", "who": "hero", "to": 1.0, "dur": 0.4},
                 {"t": 1.0, "do": "core", "who": "hero", "to": 1.8, "dur": 0.6}]
    rid = ref["id"]
    if rid in ("shadow_rise", "system"):
        climax_ev += [{"t": 0.7, "do": "vfx", "type": "system", "title": "LEVEL UP",
                       "lines": [{"text": f"{hero}  Lv. {{}}", "count": [98, 99], "color": "#fde68a"},
                                 "Skill unlocked: CONSISTENCY"], "y": 0.2, "dur": 2.6, "color": "#a78bfa"},
                      {"t": 1.05, "do": "vfx", "type": "shadow_rise", "caster": "hero", "rise": 1.2, "dur": 2.75,
                       "rows": [[0.9, 4, 0.8, 16], [0.74, 7, 2.2, 24], [0.6, 10, 3.4, 30]]}]
    elif rid.startswith("domain"):
        climax_ev.append({"t": 0.9, "do": "vfx", "type": "domain", "caster": "hero", "expand_at": 0.3, "dur": 2.8,
                          "style": ref.get("params", {}).get("style", "void")})
    elif rid == "wheel":
        climax_ev.append({"t": 0.0, "do": "vfx", "type": "wheel", "who": "hero", "turns": [0.45, 1.2], "dur": 3.8,
                          "scale": 0.9})
    elif rid == "hollow_purple":
        climax_ev += [{"t": 1.0, "do": "pose", "who": "hero", "pose": "hands_out", "dur": 0.3},
                      {"t": 1.0, "do": "vfx", "type": "hollow_purple", "caster": "hero", "charge": 0.8, "merge": 0.6,
                       "travel": 0.8, "r": 30, "big": 140, "dur": 2.8, "to": [1.3, 0.1]}]
    elif rid == "curse_marks":
        climax_ev.append({"t": 1.0, "do": "marks", "who": "hero", "to": 1.0, "dur": 0.3})
    else:
        climax_ev.append({"t": 1.0, "do": "vfx", "type": "aura", "caster": "hero"})
    shots.append({"scene": "stage", "dur": 3.8, "climax": True, "climax_at": 0.45,
                  "params": {"s": 36, "floor": 1400, "haze": 1.0},
                  "camera": {"from": {"zoom": 1.08, "y": -60}, "to": {"zoom": 0.94, "y": 0}},
                  "actors": {"hero": {"x": 0.47, "tower": {"base": 19}, "level": 0.95, "pile": 6}},
                  "events": climax_ev})
    end = _title(b, "#a78bfa", dur=3.4)
    end["params"]["size"] = 54
    shots.append(end)
    cast = {"r1": {"label": r1, "core": _core(r1, "gold"), "build": "slim"},
            "r2": {"label": r2, "core": _core(r2, "#fb923c"), "build": "slim", "flame": 1.0},
            "hero": {"label": hero, "core": _core(hero, "cyan"), "build": "slim", "eyes": "#a78bfa"}}
    sc = _wrap(b, cast, shots, ref)
    sc["style"].update({"fps": 60, "accent": "#a78bfa",
                        "grade": {"saturation": 0.9, "contrast": 1.08, "bloom": 0.5, "vignette": 0.55, "grain": 0.035}})
    sc["style"].pop("hook", None)
    return sc


BUILDERS = {"classroom_rematch": build_classroom, "duel_power": build_duel, "grind_levelup": build_grind,
            "adaptation": build_adaptation, "towers": build_towers}


def _wrap(b: dict, cast: dict, shots: list, ref: dict) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{b['hero']}_{ref['id']}_{b['template']}".lower()).strip("_")
    slug = f"{slug}_{time.strftime('%m%d_%H%M%S')}"
    return {
        "meta": {"slug": slug, "request": b.get("request", ""), "template": b["template"], "reference": ref["id"],
                 "caption": b.get("caption", ""), "hashtags": b.get("hashtags", HASHTAGS)},
        "style": {"fps": 30, "accent": ref["color"], "watermark": "@YOURHANDLE",
                  "hook": {"text": b.get("hook", ""), "from": 0.2, "to": 3.0}},
        "music": {"source": "synth", "bpm": 100, "snap_cuts": True,
                  "suggest": "dark phonk / cinematic trap with a hard drop (see: python -m engine music radar)"},
        "cast": cast,
        "shots": shots,
    }


def plan(request: str, *, use_llm: bool = True, lang: str = "ru") -> dict:
    brief = None
    if use_llm:
        try:
            brief = llm_brief(request, lang)
            print(f"brief (Claude): {brief['template']} / {brief['reference']} / {brief['hero']} vs {brief['rivals']}")
        except Exception as e:  # noqa: BLE001 - any failure falls back to the offline rules
            print(f"planner: Claude unavailable ({type(e).__name__}: {str(e)[:120]}), using keyword rules")
    if brief is None:
        brief = rule_brief(request, lang)
        print(f"brief (rules): {brief['template']} / {brief['reference']} / {brief['hero']} vs {brief['rivals']}")
    brief = _sanitize(brief)
    brief["request"] = request
    return BUILDERS[brief["template"]](brief)
