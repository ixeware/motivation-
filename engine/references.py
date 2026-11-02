"""Hidden references catalog.

RULE: the reference lives only in the image and the motion. Never put the
source title, character names or quotes into on-screen text, captions or
hashtags. `source` below is for the author only.
"""
from __future__ import annotations

REFERENCES: list[dict] = [
    {
        "id": "hollow_purple", "vfx": "hollow_purple", "color": "#9333ea",
        "source": "Jujutsu Kaisen - Gojo, Hollow Purple",
        "visual": "blue orb (attraction) at one hand + red orb (repulsion) at the other merge into a purple "
                  "sphere that erases everything in its path, leaving a dark trench with a violet rim",
        "meaning": "two opposite forces (talent vs work, fear vs desire) merged by one will become unstoppable",
        "best_for": ["EGO", "FOCUS", "PRIDE"],
        "keywords": ["пурпур", "фиолет", "годжо", "gojo", "purple", "фиолетов", "сферу", "шар", "стреля"],
    },
    {
        "id": "domain_void", "vfx": "domain", "params": {"style": "void"}, "color": "#60a5fa",
        "source": "Jujutsu Kaisen - Gojo, Unlimited Void (domain expansion)",
        "visual": "a ring expands from the hero, the room becomes deep space with streaming light, a giant iris "
                  "and floating formulas; everyone else freezes and turns blue",
        "meaning": "in your domain the work is already done: preparation makes the exam feel slow and easy",
        "best_for": ["EGO", "DISCIPLINE", "FOCUS"],
        "keywords": ["домен", "расширени", "территори", "бесконечн", "пустот", "domain", "void"],
    },
    {
        "id": "domain_shrine", "vfx": "domain", "params": {"style": "shrine"}, "color": "#ef4444",
        "source": "Jujutsu Kaisen - Sukuna, Malevolent Shrine",
        "visual": "blood-red sky with a pale sun, invisible cuts fly across the screen and slice the rivals",
        "meaning": "excuses do not survive inside a disciplined routine",
        "best_for": ["DISCIPLINE", "EGO", "RAGE"],
        "keywords": ["сукуна", "святилищ", "shrine", "разрез", "рассеч", "режет", "красн"],
    },
    {
        "id": "black_flash", "vfx": "black_flash", "color": "#dc2626",
        "source": "Jujutsu Kaisen - Itadori, Black Flash",
        "visual": "on impact: 2 inverted manga frames, then black lightning with a red rim bursts from the fist",
        "meaning": "the perfect moment comes only to the one who threw ten thousand normal punches",
        "best_for": ["HARD WORK", "DISCIPLINE"],
        "keywords": ["черная молни", "чёрная молни", "black flash", "итадори", "удар", "кулак"],
    },
    {
        "id": "blindfold", "vfx": None, "color": "#7dd3fc",
        "source": "Jujutsu Kaisen - Gojo's blindfold",
        "visual": "a black band over the eyes slides off and ice-blue eyes light up",
        "meaning": "he stops holding back",
        "best_for": ["EGO"],
        "keywords": ["повязк", "глаза", "снимает"],
    },
    {
        "id": "curse_marks", "vfx": None, "color": "#111111",
        "source": "Jujutsu Kaisen - Sukuna's marks",
        "visual": "black stripes appear under the eyes and on the forehead when the dark side takes over",
        "meaning": "ego woke up: the same pride that hurts you can work for you",
        "best_for": ["EGO", "PRIDE", "RAGE"],
        "keywords": ["метк", "проклят", "тату", "узор"],
    },
    {
        "id": "wheel", "vfx": "wheel", "color": "#e8d18a",
        "source": "Jujutsu Kaisen - Mahoraga's adaptation wheel",
        "visual": "an eight-spoked wheel above the head clanks a turn after every failure; after enough turns "
                  "the same attack no longer works",
        "meaning": "every failure is a turn of the wheel - you are adapting, not losing",
        "best_for": ["HARD WORK", "PATIENCE", "DISCIPLINE"],
        "keywords": ["колес", "махораг", "адаптац", "приспособ"],
    },
    {
        "id": "system", "vfx": "system", "color": "#38bdf8",
        "source": "Solo Leveling - the System window",
        "visual": "blue holographic window with corner brackets: [ NOTIFICATION ] Daily quest ... LEVEL UP",
        "meaning": "life as a game: daily quests compound into levels",
        "best_for": ["DISCIPLINE", "HABIT", "HARD WORK"],
        "keywords": ["систем", "уровен", "левел", "квест", "прокач", "lvl", "level"],
    },
    {
        "id": "shadow_rise", "vfx": "shadow_rise", "color": "#7c3aed",
        "source": "Solo Leveling - Arise (shadow army)",
        "visual": "dark pools open on the floor and shadow soldiers with glowing violet eyes rise behind the hero",
        "meaning": "every past failure becomes a soldier in your army",
        "best_for": ["EGO", "DISCIPLINE", "HARD WORK"],
        "keywords": ["тен", "армия", "восстан", "arise", "призыв"],
    },
    {
        "id": "aura", "vfx": "aura", "color": "#dc2626",
        "source": "One Piece - Conqueror's Haki",
        "visual": "shockwave rings + crawling black-red lightning; everyone weak-willed in the room collapses",
        "meaning": "a decided person changes the room without saying a word",
        "best_for": ["EGO", "DISCIPLINE", "CONFIDENCE"],
        "keywords": ["хаки", "король", "воля", "аура", "давлени", "haki"],
    },
    {
        "id": "afterimage", "vfx": "afterimage", "color": "#22d3ee",
        "source": "Cyberpunk: Edgerunners - Sandevistan",
        "visual": "time slows, the hero moves with rainbow afterimages while the world is frozen in teal",
        "meaning": "focus is a superpower: when you are locked in, everyone else looks slow",
        "best_for": ["FOCUS", "HARD WORK"],
        "keywords": ["сандевистан", "замедл", "время", "киберпанк", "cyberpunk", "скорост"],
    },
]

# Staging ideas that are not engine effects yet (for prompts / future work)
IDEAS = [
    {"source": "The Odyssey (2026) - tied to the mast", "visual": "hero tied to a mast while phone-shaped sirens sing",
     "meaning": "discipline = tying your hands before temptation comes"},
    {"source": "The Dark Knight Rises - the pit", "visual": "hero climbs a well and jumps without the rope",
     "meaning": "you jump further when there is no safety net"},
    {"source": "Interstellar - time on the planet", "visual": "clock spins, one hour of distraction = 7 years",
     "meaning": "time spent scrolling is time-dilated"},
    {"source": "Blue Lock - egoist / flow", "visual": "glowing eye trail, puzzle pieces, devouring the field",
     "meaning": "ego as the striker's fuel"},
    {"source": "Demon Slayer - total concentration breathing", "visual": "visible breath lines around the hero",
     "meaning": "calm, controlled effort beats rage"},
]


def by_id(ref_id: str) -> dict | None:
    for r in REFERENCES:
        if r["id"] == ref_id:
            return r
    return None


def match(text: str) -> str | None:
    t = text.lower()
    best, hits = None, 0
    for r in REFERENCES:
        h = sum(1 for k in r["keywords"] if k in t)
        if h > hits:
            best, hits = r["id"], h
    return best
