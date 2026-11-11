# 🛠️ Починка репозитория: «No file matched to **/requirements.txt»

## Что случилось (диагноз по вашему репозиторию)

Ошибка в шаге **Install system fonts and Python dependencies**:

```
No file in /home/runner/work/Libra_content_factory/Libra_content_factory matched to
[**/requirements.txt or **/pyproject.toml]
```

Это значит: **`requirements.txt` нет в репозитории**, а вместе с ним потерялась вся структура папок.
Вы загрузили **содержимое** папки `src/` (и других папок) прямо в корень — файлы «расплющились».

Как сейчас выглядит ваш репозиторий:

```
Libra_content_factory/            ← корень
├── .github/workflows/autopost.yml ✅ (на месте — хорошо!)
├── astro_engine.py          ❌ должен быть в src/
├── card_generator.py        ❌ должен быть в src/
├── fallback_writer.py       ❌ должен быть в src/
├── llm_client.py            ❌ должен быть в src/
├── main.py                  ❌ должен быть в src/
├── telegram_publisher.py    ❌ должен быть в src/
├── __init__.py              ❌ должен быть в src/
├── content_plan.md          ❌ должен быть в templates/
├── history.json             ❌ должен быть в data/
├── test_factory.py          ❌ должен быть в tests/
├── libra_avatar.png         ❌ должен быть в assets/
├── card_2026-11-11_*.png    ❌ мусор от тестовых прогонов
├── last_post.json           ❌ мусор от тестовых прогонов
└── requirements.txt         ❌ ОТСУТСТВУЕТ (из-за него и упал запуск)
```

Из-за этого `pip install -r requirements.txt` физически нечего ставить, а команда `python -m src.main`
не найдёт пакет `src`. Даже если исправить только `requirements.txt`, запуск упадёт на следующем шаге.

---

## ✅ Способ 1 (рекомендую): архив + один workflow

Вы ничего не переименовываете вручную. Понадобится 3 действия.

### 1. Скачайте архив проекта

Файл в рабочем пространстве: **`libra-content-factory.zip`** (3 МБ) — в нём уже правильная структура,
все последние правки карточек, диагностика и три workflow.

> Важно: **не распаковывайте** его. Загружать нужно сам `.zip`.

### 2. Загрузите архив в корень репозитория

1. Откройте репозиторий `Libra_content_factory`.
2. **Add file → Upload files**.
3. Перетащите `libra-content-factory.zip` в окно браузера.
4. **Commit changes** (файл должен оказаться в корне, рядом с папкой `.github`).

### 3. Добавьте workflow-починку

1. **Add file → Create new file**.
2. В поле имени введите ровно:
   ```
   .github/workflows/fix-layout.yml
   ```
3. Вставьте содержимое файла `.github/workflows/fix-layout.yml` из проекта (открывается локально в Блокноте).
4. **Commit changes**.

### 4. Запустите починку

1. Вкладка **Actions** → слева **Fix repo layout (one-time)**.
2. Справа **Run workflow** → **Run workflow**.
3. Дождитесь зелёной галочки (~1 минута). В логе шага **Verify structure** увидите:

```
=== Корень репозитория ===
...
✅ requirements.txt
✅ src/main.py
✅ src/astro_engine.py
✅ src/card_generator.py
✅ src/llm_client.py
✅ src/fallback_writer.py
✅ src/telegram_publisher.py
✅ .github/workflows/autopost.yml

🎉 Структура корректна — можно запускать «Libra Content Factory Autopost»
```

Workflow сам: распакует архив, разложит файлы по папкам, удалит дубли и мусорные PNG из корня,
перезапишет `autopost.yml` актуальной версией и закоммитит результат. Архив после распаковки удаляется.

### 5. Запустите завод

**Actions → Libra Content Factory Autopost → Run workflow**, `dry_run: true`.

---

## 🧰 Способ 2: без архива, старые файлы переносятся в папки

Если архив загрузить не получается — добавьте только `fix-layout.yml` (пункт 3 выше) и запустите его.
Workflow увидит, что архива нет, и **перенесёт** существующие «плоские» файлы по правильным папкам.

> ⚠️ Но `requirements.txt` в вашем репозитории сейчас **отсутствует** — его придётся создать вручную:
> **Add file → Create new file** → имя `requirements.txt` → вставить две строки:
> ```text
> requests>=2.31.0
> pillow>=10.0.0
> ```
> → **Commit changes** → и только потом запускать `fix-layout`.

После этого структура станет правильной, но версии `card_generator.py` и остальных модулей останутся
**старыми** (без исправлений подписи `@channel`, колец и защиты `dry_run` при push). Чтобы получить
свежие — всё же загрузите архив по Способу 1.

---

## ✋ Способ 3: вручную переименовать/переместить (без workflow)

GitHub умеет «перемещать» файл: открываете файл → карандаш ✏️ (**Edit**) → меняете **имя файла**
в поле над текстом (можно с `/`) → **Commit changes**. Папка создастся автоматически.

Точная карта переносов (12 файлов):

| Сейчас в корне | Должно стать |
|---|---|
| `astro_engine.py` | `src/astro_engine.py` |
| `card_generator.py` | `src/card_generator.py` |
| `fallback_writer.py` | `src/fallback_writer.py` |
| `llm_client.py` | `src/llm_client.py` |
| `main.py` | `src/main.py` |
| `telegram_publisher.py` | `src/telegram_publisher.py` |
| `__init__.py` | `src/__init__.py` |
| `content_plan.md` | `templates/content_plan.md` |
| `history.json` | `data/history.json` |
| `test_factory.py` | `tests/test_factory.py` |
| `libra_avatar.png` | `assets/libra_avatar.png` |

Плюс создать/добавить в корень:

| Файл | Где взять |
|---|---|
| `requirements.txt` | создать вручную (2 строки, см. Способ 2) |
| `README.md` | загрузить из проекта |
| `.env.example` | загрузить из проекта |
| `.gitignore` | загрузить из проекта |
| `.github/workflows/autopost.yml` | перезаписать актуальной версией из проекта |
| `.github/workflows/check-setup.yml` | создать (Add file → Create new file) |

И **удалить** мусор из корня: `card_2026-11-11_forecast.png`, `card_2026-11-11_love.png`,
`card_2026-11-11_tarot.png`, `card_2026-11-14_love.png`, `card_2026-11-24_tarot.png`, `last_post.json`.
(Открыть файл → значок корзины 🗑️ → Commit changes.)

---

## 🔍 Как проверить, что структура правильная

Откройте корень репозитория — должно быть **ровно так**:

```
.github/workflows/autopost.yml
.github/workflows/check-setup.yml
.github/workflows/fix-layout.yml
assets/libra_avatar.png
data/history.json
src/__init__.py
src/astro_engine.py
src/card_generator.py
src/fallback_writer.py
src/llm_client.py
src/main.py
src/telegram_publisher.py
templates/content_plan.md
templates/SECRETS.md
tests/test_factory.py
.env.example
.gitignore
README.md
requirements.txt
```

Быстрые ссылки для проверки (подставьте свой логин):

```
https://github.com/LOGIN/Libra_content_factory/blob/main/requirements.txt
https://github.com/LOGIN/Libra_content_factory/blob/main/src/main.py
```

Обе должны открываться. Если `requirements.txt` отдаёт 404 — структура ещё не исправлена.

---

## 💡 Почему так вышло и как загружать правильно

Папка `src` не «исчезла»: при загрузке через веб вы перетащили **отдельные файлы**, а не папки.
Чтобы структура сохранилась, нужно либо:

- перетаскивать **папки целиком** (`src`, `templates`, `tests`, `data`, `assets`) — браузер сохранит вложенность;
- либо (надёжнее) **не загружать ничего вручную**, а распаковать архивный подход: архив + `fix-layout`;
- либо использовать **GitHub Desktop**, который сохраняет структуру без сюрпризов.

> ❗ Не перетаскивайте саму папку `libra-content-factory` — тогда внутри репозитория появится
> лишняя вложенная папка, и GitHub снова не найдёт `.github/workflows/`.

---

## После починки

1. Проверьте секреты: **Actions → Check Setup (diagnostics) → Run workflow**.
2. Запустите пост: **Actions → Libra Content Factory Autopost → Run workflow**, `dry_run: true`.
3. Скачайте артефакт `libra-post-preview`, посмотрите карточку.
4. Повторите с `dry_run: false` — пост уйдёт в канал.
