# motivation- : движок мотивационных роликов

Python-движок рендерит вертикальные мотивационные ролики в стиле «белые стикмены + ярлыки-архетипы + скрытая отсылка к аниме или фильму».

- Новый ролик по запросу пользователя: следуй скиллу `.claude/skills/make-video/SKILL.md`.
- Формат сценария: `docs/SCENARIO.md`. Эталон: `scenarios/talent_vs_hardwork_purple.json`.
- Стиль и атрибутика: `docs/STYLE_GUIDE.md`, `docs/ATTRIBUTES.md`. Промпты для обложек: `docs/GPT_IMAGE_PROMPTS.md`.
- 3D-ролики (Blender + Mixamo, toon-фигуры с контуром): `docs/3D.md`. Один модуль на ролик в `engine/blender/films/`.

## Команды
```bash
pip install -r requirements.txt        # на Linux ещё: apt-get install -y libegl1 ffmpeg
python -m engine make "запрос"         # запрос -> сценарий -> видео
python -m engine render scenarios/x.json [--preview]
python -m engine still scenarios/x.json 12.5 --scale 0.4
python -m engine music radar | fetch <url> | research <hashtags> | analyze <file>
python -m engine refs | poses | scenes
python -m engine film <name> [--preview] [--still 30,120]   # 3D-ролик (pip install bpy==5.2.3)
python -m engine mocap search|fetch|list                    # клипы Mixamo (токен своей сессии, не в репо)
```

## Устройство
- `engine/render/`: `rig.py` (фигуры и позы), `scenes.py` (сцены), `vfx.py` (отсылки), `renderer.py` (камера, глубина резкости, пост, ffmpeg).
- `engine/audio/`: процедурные SFX, музыкальная подложка, анализ битов и дропа, микс.
- `engine/music/tiktok.py`: радар звуков ниши (yt-dlp), загрузка звука, официальный TikTok Research API.
- `engine/planner.py`: бриф (Claude API или правила) и сборка сценария из шаблонов.
- `engine/blender/`: 3D-путь: `kit.py` (сцена, материалы, скелет, IK), `props.py`, `mocap.py`, `post.py`, `run.py`, `films/`.

## Правила
- Весь текст в видео только на английском (ярлыки, субтитры, окна, финальная карточка). Подпись к посту и хэштеги тоже на английском. `make` по умолчанию `--lang en`.
- В тексте на экране, подписи и хэштегах никогда не называть аниме, фильмы, персонажей и техники. Отсылка только визуальная.
- `output/` не коммитить. Сценарии коммитить.
- Токен Mixamo никогда не коммитить и не просить вставить в чат. Клипы Mixamo (`assets/mocap/cache/`) не коммитить.
