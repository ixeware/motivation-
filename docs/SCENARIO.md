# Формат сценария (JSON)

> Весь текст в кадре — только на английском: ярлыки, `text`, хук, окна `system`, строки финальной карточки, подстрочник.

Сценарий — это список планов (`shots`). У каждого плана своя сцена, актёры, камера и события на таймлайне.
Время событий отсчитывается от начала плана. Примеры: `scenarios/*.json`.

```jsonc
{
  "meta":  {"slug": "my_video", "caption": "подпись к посту", "hashtags": ["motivation", "ego"]},
  "style": {"fps": 30, "accent": "violet", "seal": "E", "watermark": "@handle",
            "hook": {"text": "TALENT VS HARD WORK", "from": 0.2, "to": 3.0},
            "grade": {"saturation": 0.92, "contrast": 1.06, "bloom": 0.55, "vignette": 0.62, "grain": 0.07}},
  "music": {"source": "synth" | "tiktok" | "file" | "library",
            "grid": {"t0": 0.084, "period": 0.49175},   // точная сетка долей (из `music grid`), для пульсаций
            "loop_from": 20.25,     // трек короче ролика: с какого места зациклить (позиция в той же фразе)
            "sfx_gain": 0.75,       // громкость эффектов относительно песни
            "url": "https://www.tiktok.com/@.../video/...",   // source=tiktok
            "file": "assets/music/track.mp3",                 // source=file
            "start": null,          // null = автоматически: дроп трека совпадает с кульминацией
            "snap_cuts": true,      // склейки на биты
            "gain": 0.75, "bpm": 100},
  "cast": {"ego": {"label": "EGO", "core": "violet", "eyes": "#7dd3fc"}},
  "shots": [
    {"scene": "classroom", "dur": 3.4,
     "climax": false, "climax_at": 0.0,           // один план с climax=true: его момент ставится на дроп
     "in": "cut" | "flash" | "impact" | "fade" | "glitch" | "whoosh", "out": "cut" | "fade",
     "params": {...},                              // параметры сцены, см. ниже
     "camera": {"from": {"zoom": 1.0, "x": 0, "y": 0, "on": "ego"}, "to": {"zoom": 1.1},
                "ease": "sine", "dof": 1.0, "focus": "main"},
     "actors": {"ego": {"pose": "sit", "x": 0.5, "s": 64, "facing": 1, "level": 0.2, "sheet": "C",
                        "band": 0, "eyes": 0, "marks": 0, "core": 1.0, "zzz": false,
                        "mods": {"writing": 1, "board": 1, "walk": 1, "fight": 1, "float": 1, "shake": 1}}},
     "events": [ {"t": 1.0, "do": "...", ...} ]}
  ]
}
```

## Сцены (`scene`)

| Сцена | Вид | Параметры |
|---|---|---|
| `classroom` | фронтально, ряды парт (как в референсе) | `sky` (night/dawn/цвет), `walker` {from,to,t0,t1,s}, `extras` 0/1, `front_heads` |
| `closeup` | один актёр крупно, сильный боке | `sky`, `desk` |
| `study` | сбоку, ночная учёба: лампа, окно ночь→рассвет, часы, книги | `hours` [23, 30.5], `books` [1, 8], `dawn`, `dawn_at`, `lamp_off` |
| `board` | сбоку, пишет на доске | `lines` [...], `reveal_from`, `reveal_until` |
| `arena` | сбоку, тёмная сцена для боя | `spot`, `spot_c`, `tint`, `horizon`, `floor`, `shadows` |
| `void` | фронтально, пустая сцена (раскрытие героя, территория) | как у `arena` |
| `tunnel` | перспектива: камера улетает назад сквозь идеально круглую дыру в школе (стена класса → коридор со шкафчиками → кабинет → фасад → ночь), герой стоит в глубине | `cam` [[t, z], ...] путь камеры, `F`, `axis_y`, `walls` [{z, th, kind: lockers / lab / facade}], `back_z`; актёры: `lx` (смещение), `seated`, `pose` |
| `stage` | фронтально, чёрная сцена: глянцевый пол, прожектор над каждым, башни из блоков, ярлыки на полу (уровень новых роликов референса) | `s` (размер фигур), `floor`, `reflect` (0..1), `haze`, `spot`, `spot_w`, `label_pos`, `block_w`, `block_h`, `spots` [{x, w, a}] |
| `title` | финальная карточка | `lines` (слово с `*` красится в акцент), `sub`, `accent`, `size`, `seal`, `rule` (черта под цитатой, по умолчанию выкл.) |

## Позы (`python -m engine poses`)

Фронтальные: `sit`, `sit_relaxed`, `sleep`, `head_in_hands`, `hands_on_head`, `arms_up`, `fist_up`, `stand`, `stand_proud`,
`cast`, `cast_sit`, `heaven`, `hands_out`, `hands_together`, `fire_right`, `fire_left`, `shrug`, `slumped`,
`sit_think`, `sit_scratch`, `sit_stretch`,
`pick_l`, `pick_r`, `place_r`, `place_l`, `carry`, `squat`, `squat_rest`, `squat_despair`, `squat_slump`, `kneel_front`.
Боковые: `sit_side`, `write`, `think_side`, `stand_side`, `board_write`, `point`, `stance`, `punch`, `punch_back`,
`guard`, `hit`, `kick`, `cast_side`, `float_side`, `victory_side`, `kneel_side`.

## События (`do`)

| do | Поля | Что делает |
|---|---|---|
| `pose` | who, pose, dur, ease, mods | плавный переход в позу |
| `move` | who, x (0..1), dy, yoff, dur | перемещение |
| `sheet` / `sheet_off` | who, mark, score (`"92"`, `"100"`), glow (цвет свечения) | лист с оценкой и красными баллами (звук бумаги и печати добавляется сам) |
| `level` | who, to (0..1), dur, text | XP-полоса и подпись (`MAX`, `LV 2`) |
| `core` / `eyes` / `band` / `marks` / `tint` | who, to, dur | ядро, глаза, повязка, метки, тонировка |
| `glitch` | who, dur | глитч ярлыка |
| `label` | who, text | сменить ярлык |
| `zzz` | who, on | «Z z z» |
| `emote` | who, text (`?`, `!`, `...`), dur | белый пузырь-реплика над головой |
| `stack` | who, until, rate (блоков в секунду) | цикл «взял блок → положил на башню», башня растёт (нужен `tower` у актёра) |
| `dim` | who, to, dur | персонаж сдался: серый, без свечения, тусклый ярлык |
| `flame` | who, to, dur | огонь на голове (1 горит, 0 погас и дымится) |
| `spot` | who, to, dur | яркость его прожектора на `stage` |
| `sparkle` | who, to, dur, hold | искорка ✦ у головы |
| `fade` / `hide` / `show` | who, to, dur | прозрачность |
| `face` | who, facing | развернуть |
| `shake` / `flash` / `impact` / `punch` | amp, dur, color, frames | тряска, вспышка, манга-кадр, зум-удар |
| `text` | text, pos (top/center/bottom), dur, size, color, fade_in, fade_out | моно-субтитр; `fade_in: 0` — продолжение того же титра в следующем плане |
| `vfx` | type + параметры | эффект из списка ниже |
| любое + `sfx` | sfx, gain | звук: boom, hit, crack, whoosh, riser, hum, drone, rumble, chime, clank, paper, stamp, tick, slash |

## Эффекты (`vfx`)

| type | Главные параметры |
|---|---|
| `hollow_purple` | caster, charge, merge, travel, r, big, from, to, targets, length, offset (продолжить в следующем плане) |
| `energy_orb` | at ([x,y] доли кадра или {who, at}), r, grow, color, layer (back/main/fx) |
| `domain` | caster, style (void/shrine), expand_at, frozen [...], texts [...] |
| `black_flash` | at {who, at: hand_r}, targets, size |
| `impact` | frames |
| `system` | title, lines (строки или {"text": "Level {}", "count": [1, 2]}), y, w, color |
| `shadow_rise` | caster, count, rise, spread, scale |
| `wheel` | who, turns [t...], scale, color |
| `aura` | caster, targets |
| `afterimage` | who, count, gap |
| `speedlines` / `slash` | a, color / count, color |
| `light_pillar` | at (например `{"who": "hero", "at": "tower"}`), width, color, floor |
| `purple_launch` | at, r, hold, travel — пурпурная сфера летит прямо в камеру и заливает кадр |
| `glance` | who, targets [...], rate — пунктирный «взгляд» в чужой лист (в паре с модом `look_around`) |
| `hollow_purple` + флаги | `"fire": false` — только зарядка и слияние (без выстрела), `"eyes": false` — глаза не загораются (повязка) |
| `shadow_rise` + `rows` | ряды за героем: `[[масштаб, сколько, отступ_назад, ширина], ...]` |

`at` для эффектов: `[0.5, 0.8]` (доли кадра) или `{"who": "ego", "at": "hand_r|hand_l|hands|head|above|feet|front|core|tower", "dx": 0, "dy": -1.6}` (dx и dy в радиусах головы).

## Поля актёра в плане

`pose`, `x`, `s`, `facing`, `level`, `level_text`, `sheet`, `band`, `eyes`, `marks`, `core`, `zzz`, `mods`,
`build` (`chunky` | `slim`), `label_pos` (`head` | `floor`), `tower` {`base`, `side`}, `pile` (блоков в запасе),
`dim`, `flame`, `spot`, `sparkle`, `layer`, `alpha`, `yoff` (поднять/опустить, например встал из-за парты).

Моды (`mods`): `writing`, `board`, `walk`, `fight`, `float`, `shake`, `pant`, `sweat` (капли пота),
`look_around` (+ `look_rate`, `look_offset`) — вертит головой и заглядывает к соседям. Чтобы взгляды
попадали в доли: `look_rate = 1 / (2 * доля)`, `look_offset = 1.5708`.

## Качество

- `style.fps: 60` для финала, как у референса. Рендер примерно в 2 раза дольше.
- `params.reflect` у сцены: сила отражения в полу (0 выключает).
- `text` по умолчанию в стиле `sub` (тонкий моно-субтитр сверху), для крика — `"style": "bold"`. Перенос строки — `\n`.

Длинный эффект через несколько планов: в следующем плане повторяешь тот же `vfx` с `"offset": <секунд уже прошло>`.

## Монтаж под чужую песню (TikTok-эдит)

1. `python -m engine music strip edit.mp4 --ours output/<slug>/final.mp4` — чистая песня без нашего старого звука.
2. `python -m engine music grid assets/music/user/<file>.wav` — доля, первая доля, начала тактов и 4-тактовых фраз.
3. Длительности планов кратны долям (лучше — тактам), кульминация (`climax`) — на начало фразы.
   `music: {"source": "file", "file": ..., "start": 0, "snap_cuts": false, "grid": {...}}`.
4. В TikTok ставь тот же звук с той же точки старта, что в присланном эдите.
