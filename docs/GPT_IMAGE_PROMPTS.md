# Промпты для GPT Image: перегенерация скриншота в наш стиль

Как пользоваться:
1. Возьми скриншот из ролика-референса или `output/<ролик>/cover.png`, который движок рендерит сам.
2. Прикрепи его к запросу и вставь **мастер-промпт** (раздел 1). Если нужна конкретная сцена, допиши блок сцены из раздела 2.
3. Для лёгкого сдвига стиля добавь одну строку из раздела 3.

Промпты на английском: модели изображений так точнее. Имён персонажей и названий тайтлов в промптах **нет** намеренно. Так модель не рисует чужого персонажа, а отсылка остаётся «для своих».

---

## 1. Мастер-промпт (edit по прикреплённому скриншоту)

```text
Use the attached screenshot as the composition and pose reference. Keep the camera angle, the layout of the
figures, the desks/props and the overall mood, but redraw it in this exact visual style:

STYLE: minimal 3D-rendered stick figures made of soft matte white "pill" shapes: a perfectly round head with NO
face, a rounded capsule torso, thick capsule arms and legs with round ends, a subtle white rim glow around every
figure. Background in deep charcoal greys (#16171a to #24252a), cinematic shallow depth of field: the main row is
sharp, the background and foreground objects are strongly blurred with creamy bokeh. Soft film grain, gentle
vignette, high-end motion-design look, vertical 9:16.

SIGNATURE DETAILS (must be visible):
- Each figure has a small glowing CORE in the center of its chest: a tiny bright dot with a soft colored halo.
  Colors by archetype: EGO = violet (#a855f7), DISCIPLINE = icy cyan (#38bdf8), TALENT = gold (#fbbf24),
  HARD WORK = pale blue (#7dd3fc). The cores are the ONLY saturated colors on the figures.
- Above each head a small label in a monospace bold font, uppercase, widely letter-spaced (e.g. "E G O"), white
  with a faint glow. Directly under the label a thin progress bar in the color of that figure's core, partially
  filled.
- Graded paper sheets float above some labels: off-white paper, grey text lines, a red hand-stamped circled
  letter grade (A, A-, C, A+).

LIGHTING: the world is almost monochrome; color comes only from the cores, windows (deep night blue or warm
dawn orange), a warm desk lamp if present, and red stamps.

DO NOT: add faces, mouths, eyes (unless asked), hair, clothes, logos, watermarks, brand names, anime characters
or any extra text besides the labels and grades. All visible text must be in English. Keep it clean and readable
on a phone.
```

## 2. Блоки сцен (дописать к мастер-промпту)

### 2.1 Класс: три архетипа (оригинальный формат + наша атрибутика)
```text
SCENE: a dark classroom at night. Three figures sit behind dark grey box desks in the main row: left "DISCIPLINE"
(cyan core, paper with red "A" above), center "EGO" (violet core, paper with red "C" above, both hands on his
head in frustration), right "TALENT" (gold core, head down asleep on folded arms, small "Z z z" letters, paper
with red "A-"). Rows of blurred dimmer students behind, two tall windows glowing deep blue, a wall clock.
A blurred white figure walks across the foreground. The bright white sheets on the desks glow softly.
```

### 2.2 Пурпурная сфера (пример из запроса)
```text
SCENE: a dark void stage with a reflective floor. In the middle, two figures "TALENT" (gold core) and "HARD WORK"
(pale blue core) fight in side view: one throws a punch, the other blocks. Behind and below them, close to the
floor, a huge sphere of purple energy is forming: a white-hot center, violet plasma, thin swirling rings, small
violet lightning arcs, particles being pulled inward; it tints the floor purple. Above, slightly out of focus,
a third figure "EGO" (violet core) floats calmly with a black band over his eyes, one hand raised with two
fingers up. Next to his left hand floats a small blue orb, next to his right hand a small red orb.
Mood: the calm before an annihilating strike.
```

### 2.3 Момент выстрела (кадр-обложка)
```text
SCENE: the frame is split by a diagonal trench of pure black void with a glowing violet rim and rising violet
embers, as if a giant purple sphere just tore through the scene from the bottom right corner. The sphere is still
visible leaving the frame top-left: white-hot core, violet halo, swirling rings, a white shockwave ring at its
origin. Where two figures stood there is nothing left but fading particles. Slight chromatic aberration and
motion streaks. Dramatic, anime-impact-frame energy, but still the same minimal white-figure style.
```

### 2.4 Расширение территории в классе
```text
SCENE: the same classroom, but a perfect circle expands from the "EGO" figure: inside the circle the room
has become deep space (navy to black) with hyperspace light streaks rushing outward, a giant glowing blue
ring like an iris behind him, and floating handwritten math formulas drifting in the void. EGO sits upright,
eyes glowing icy blue, one hand raised with two fingers up. The other students are frozen, tinted dark blue.
A paper with a red "A+" floats above EGO's label.
```

### 2.5 Армия теней
```text
SCENE: a single figure "DISCIPLINE" (cyan core, progress bar full) stands center on a dark stage. Behind him,
six dark silhouettes in the same pill-figure style rise out of black pools on the floor, rimmed with violet
light, each with two small glowing violet eyes, purple mist curling around their legs. A blue holographic
game-like window floats above: "[ LEVEL UP ]".
```

### 2.6 Колесо адаптации
```text
SCENE: side view on a dark stage: a large figure labeled "FEAR" (red core) punches a smaller figure labeled "YOU"
(white core) who blocks. Above "YOU"'s head floats an eight-spoked golden wheel with round knobs at the end of
every spoke, mid-rotation, glowing and leaving a short motion blur.
```

### 2.7 Окно квеста (ночная учёба)
```text
SCENE: side view, a figure "DISCIPLINE" sits at a desk writing under a warm desk lamp at night, a growing
stack of books, a dark window with deep blue night, a wall clock. In the upper third floats a translucent dark
navy holographic panel with a thin cyan border, corner brackets and faint scanlines, title "[ DAILY QUEST ]"
and two monospace lines "Focus hours 8/8" and "Problems 100/100".
```

### 2.8 Финальная карточка / превью
```text
SCENE: almost black background with a soft violet radial glow in the center. Big bold condensed sans-serif text
in white, centered on three lines: "TALENT ARGUED." / "WORK ARGUED." / "EGO REFUSED TO LOSE." with the word
"LOSE." in glowing violet. Under it a thin glowing violet line and a small letter-spaced monospace subtitle
"MAKE IT FUEL, NOT A CAGE". At the bottom a small tilted square red ink seal with the letter "E".
```

### 2.9 Сцена с прожекторами и зеркальным полом (уровень новых роликов референса)
```text
SCENE: a pitch-black stage with a glossy, mirror-like black floor. Three slim white figures (smaller round heads,
long capsule limbs, thin dark outline around every part) stand in a row, each lit by its own soft volumetric
spotlight beam from above with a pool of light on the floor and tiny dust particles in the beam. Next to each
figure a tower of glowing white rounded blocks on a small black pedestal, a pile of grey blocks on the other side.
Left: "TALENT" squatting with a hand on his chin, a small four-point sparkle near his head, greyed out, his spot dim.
Middle: "MOTIVATION" slumped with head down, a dying red flame and smoke above his head, greyed out.
Right: "DISCIPLINE" bright white, placing a block on the tallest tower, cyan core glowing in his chest.
Everything is reflected in the floor, the reflection softly fading downward. Labels are written on the floor under
each figure in a bold monospace font with wide letter-spacing. Tiny watermark text near the bottom.
```

### 2.10 Финал «армия»
```text
SCENE: the same black glossy stage. A slim white figure "DISCIPLINE" stands with hands on hips next to a very tall
tower of glowing white blocks; from the top of the tower a pillar of white light shoots up to the sky with a
four-point lens flare. Behind him three rows of dark shadow figures with small glowing violet eyes rise from black
pools on the floor, violet mist at their feet, the back rows smaller. Everything is mirrored in the glossy floor.
A dark navy holographic panel with violet border floats at the top: "[ LEVEL UP ]".
```

## 3. Небольшой сдвиг стиля (одна строка на выбор)

```text
SHIFT A (porcelain): figures look like glossy white porcelain with subtle subsurface glow, the rest unchanged.
SHIFT B (clay): figures are soft matte clay with tiny fingerprints texture, warm studio light, the rest unchanged.
SHIFT C (ink manga): render the same scene as a high-contrast black & white manga panel with screentone and
         speed lines; keep only the core colors and the effect color in color.
SHIFT D (chalk): everything drawn as glowing chalk lines on a dark blackboard; cores and effects as colored chalk.
SHIFT E (neon outline): figures are dark with thin neon outlines in their core color; cyberpunk rain reflections.
```

## 4. Если модель «уплывает»

- Лица появились: допиши `faceless, featureless round heads, no eyes, no mouth`.
- Лишний текст: `the ONLY text allowed is: "EGO", "TALENT", "HARD WORK", "A+"`.
- Слишком цветно: `desaturated monochrome world, saturation only in the chest cores and the energy effect`.
- Потерялась композиция: `match the attached image's composition exactly, change only the rendering style`.
