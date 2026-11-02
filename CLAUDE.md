# motivation- : движок мотивационных роликов

Python-движок рендерит вертикальные мотивационные ролики в стиле «белые стикмены + ярлыки-архетипы + скрытая отсылка к аниме или фильму».

- Новый ролик по запросу пользователя: следуй скиллу `.claude/skills/make-video/SKILL.md`.
- Формат сценария: `docs/SCENARIO.md`. Эталон: `scenarios/talent_vs_hardwork_purple.json`.
- Стиль и атрибутика: `docs/STYLE_GUIDE.md`, `docs/ATTRIBUTES.md`. Промпты для обложек: `docs/GPT_IMAGE_PROMPTS.md`.

## Команды
```bash
pip install -r requirements.txt        # на Linux ещё: apt-get install -y libegl1 ffmpeg
python -m engine make "запрос"         # запрос -> сценарий -> видео
python -m engine render scenarios/x.json [--preview]
python -m engine still scenarios/x.json 12.5 --scale 0.4
python -m engine music radar | fetch <url> | research <hashtags> | analyze <file>
python -m engine refs | poses | scenes
```

## Устройство
- `engine/render/`: `rig.py` (фигуры и позы), `scenes.py` (сцены), `vfx.py` (отсылки), `renderer.py` (камера, глубина резкости, пост, ffmpeg).
- `engine/audio/`: процедурные SFX, музыкальная подложка, анализ битов и дропа, микс.
- `engine/music/tiktok.py`: радар звуков ниши (yt-dlp), загрузка звука, официальный TikTok Research API.
- `engine/planner.py`: бриф (Claude API или правила) и сборка сценария из шаблонов.

## Правила
- Весь текст в видео только на английском (ярлыки, субтитры, окна, финальная карточка). Подпись к посту и хэштеги тоже на английском. `make` по умолчанию `--lang en`.
- В тексте на экране, подписи и хэштегах никогда не называть аниме, фильмы, персонажей и техники. Отсылка только визуальная.
- `output/` не коммитить. Сценарии коммитить.
