# 📤 Подробная инструкция: загрузка проекта на GitHub

Пошаговое руководство: от создания репозитория до первого автоматического поста.
Ничего платить не нужно — GitHub даёт бесплатные минуты Actions (для Private-репозитория 2000 минут/мес; наш скрипт тратит ~15 минут в месяц).

---

## Часть 0. Что именно нужно загрузить

Загружать нужно **содержимое** папки `libra-content-factory`, а не саму папку.
Правильная структура в корне репозитория:

```text
libra-content-factory/          ← репозиторий (корень)
├── .github/
│   └── workflows/
│       └── autopost.yml        ← РАСПИСАНИЕ (скрытая папка!)
├── assets/
│   └── libra_avatar.png
├── data/
│   └── history.json
├── src/
│   ├── __init__.py
│   ├── astro_engine.py
│   ├── card_generator.py
│   ├── fallback_writer.py
│   ├── llm_client.py
│   ├── main.py
│   └── telegram_publisher.py
├── templates/
│   └── content_plan.md
├── tests/
│   └── test_factory.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

❌ **НЕ загружайте:** папку `output/`, `__pycache__/`, файл `.env` (если уже создали — там ваши токены).
❌ **НЕ создавайте** внутри репозитория вложенную папку `libra-content-factory/libra-content-factory/` — так GitHub не найдёт `autopost.yml`, и расписание не заработает.

---

## Часть 1. Создаём пустой репозиторий на GitHub

1. Войдите на **[github.com](https://github.com)** (или зарегистрируйтесь).
2. Справа вверху нажмите **`+`** → **New repository**.
3. Заполните:
   - **Repository name:** `libra-content-factory`
   - **Visibility:** **Private** ✅
   - **НЕ ставьте галочки** «Add a README file», «Add .gitignore», «Choose a license» — репозиторий должен быть пустым.
4. Нажмите **Create repository**.

---

## Часть 2. Загрузка файлов — выберите один способ

### Способ 1. GitHub Desktop (проще всего, без терминала)

1. Установите **[GitHub Desktop](https://desktop.github.com/)** и войдите в аккаунт.
2. **File → Add local repository…** → выберите папку `libra-content-factory`.
3. Если появится надпись *"This directory does not appear to be a Git repository"* — нажмите ссылку **create a repository** → оставьте имя → **Create repository**.
4. Нажмите **Publish repository** (вверху).
5. Галочка **Keep this code private** → **Publish repository**.
6. Всё, скрытая папка `.github` загрузится автоматически.

---

### Способ 2. Через браузер (без установки программ)

> Проводник Windows и Finder на macOS **скрывают** папку `.github`, поэтому её придётся создать на сайте отдельно.

1. Откройте созданный репозиторий → нажмите ссылку **uploading an existing file**.
2. Откройте папку `libra-content-factory` у себя на компьютере, перетащите в окно браузера её **содержимое**:
   - папки `assets`, `data`, `src`, `templates`, `tests`
   - файлы `.env.example`, `.gitignore`, `README.md`, `requirements.txt`
3. Внизу нажмите **Commit changes**.
4. Теперь создайте расписание вручную:
   - На главной странице репозитория: **Add file → Create new file**
   - В поле **Name your file...** введите целиком:
     ```text
     .github/workflows/autopost.yml
     ```
     (как только введёте первый `/`, GitHub сам создаст папки `.github` и `workflows`)
   - Откройте файл `libra-content-factory/.github/workflows/autopost.yml` в Блокноте (или TextEdit → Формат → Обычный текст), скопируйте **всё содержимое** и вставьте в большое поле на сайте.
   - Нажмите **Commit changes…** → **Commit changes**.

---

### Способ 3. Через терминал `git` (1 минута)

Windows: правый клик в папке → **Open Git Bash here**. macOS/Linux: обычный терминал.

```bash
cd путь/к/папке/libra-content-factory

git init
git add .
git commit -m "Initial commit: Libra content factory"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

`USERNAME` — ваш логин GitHub, `REPO` — имя репозитория.

Если при `git push` просят пароль — введите **Personal Access Token**, а не пароль аккаунта:
GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token** → галочка `repo` → скопируйте токен и вставьте его вместо пароля.

---

## Часть 3. Проверка после загрузки

1. Откройте главную страницу репозитория. В корне должны быть видны:
   `.github`, `assets`, `data`, `src`, `templates`, `tests`, `README.md`, `requirements.txt`
   > Если папка `.github` не видна в веб-интерфейсе — это нормально, если она есть в структуре. Проверить можно так: откройте напрямую
   > `https://github.com/USERNAME/REPO/blob/main/.github/workflows/autopost.yml` — должен открыться YAML-файл.
2. Откройте вкладку **Actions**:
   - Если видите список **Libra Content Factory Autopost** — всё загружено верно ✅
   - Если вкладка пустая и предлагает *"Get started with GitHub Actions"* — файл расписания не попал в репозиторий. Вернитесь к п. 4 Способа 2 или загрузите проект через GitHub Desktop.

---

## Часть 4. Секреты и переменные

Репозиторий → **Settings → Secrets and variables → Actions**

### Вкладка **Secrets** (New repository secret)

| Имя | Обязательно | Значение |
|---|---|---|
| `TG_BOT_TOKEN` | ✅ | токен от [@BotFather](https://t.me/BotFather) |
| `TG_CHANNEL_ID` | ✅ | `@username_канала` или `-1001234567890` |
| `TG_ADMIN_ID` | только для `draft` | ваш личный chat_id от [@userinfobot](https://t.me/userinfobot) |
| `GEMINI_API_KEY` | по желанию | бесплатный ключ [Google AI Studio](https://aistudio.google.com/apikey) |
| `GROQ_API_KEY` | по желанию | бесплатный ключ [Groq Console](https://console.groq.com/keys) |
| `OPENROUTER_API_KEY` | по желанию | бесплатный ключ [OpenRouter](https://openrouter.ai/keys) |

> Если не задать ни одного ключа ИИ — завод продолжит работать на встроенном офлайн-генераторе, астрономия и карточки при этом остаются реальными. В GitHub Actions дополнительно уже доступен `GITHUB_TOKEN`, который даёт бесплатный доступ к GitHub Models (права `models: read` прописаны в workflow).

### Вкладка **Variables** (New repository variable) — необязательно

| Имя | Пример | Зачем |
|---|---|---|
| `CHANNEL_HANDLE` | `@vesy_prognoz` | подпись в подвале карточки и в конце поста |
| `PUBLISH_MODE` | `auto` или `draft` | сразу в канал / сначала черновик админу |
| `TIMEZONE_OFFSET` | `3` | часовой пояс для выбора слота (Москва = 3) |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | свой OpenAI-совместимый провайдер |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | конкретная модель |

---

## Часть 5. Первый запуск

1. Вкладка **Actions** → в левом меню **Libra Content Factory Autopost**.
2. Справа кнопка **Run workflow**:
   - `slot` → `auto`
   - `dry_run` → **true** (проверка без публикации)
   - **Run workflow** → обновите страницу через 20 секунд, появится запуск.
3. Откройте запуск → внизу раздел **Artifacts** → скачайте `libra-post-preview` (zip) → внутри готовая PNG-карточка и `last_post.json` с текстом поста.
4. Если карточка и текст нравятся — запустите ещё раз с `dry_run` → **false**. Пост появится в Telegram-канале.
5. Дальше всё работает само: **08:30 МСК** и **19:00 МСК** каждый день.

---

## Частые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| Вкладка Actions пустая | `.github/workflows/autopost.yml` не на месте | Проверьте прямой URL файла (см. Часть 3), при необходимости создайте файл через **Add file → Create new file** |
| `Telegram API error (400): chat not found` | бот не админ канала или неверный `TG_CHANNEL_ID` | добавьте бота в администраторы канала с правом публикации; для закрытого канала используйте `-100...` |
| `Telegram API error (403): bot is not a member` | канал сменился или бот удалён | перепроверьте права администратора |
| Запуск прошёл, но `published: false` | был включён `dry_run` | повторите запуск с `dry_run = false` |
| Не запускается по расписанию | GitHub отключает cron в неактивных репозиториях (60 дней без активности) | зайдите в Actions и нажмите **Enable workflow**, либо раз в месяц делайте любой коммит |
| Текст поста не на русском / странный | сработал не тот LLM-провайдер | удалите лишние ключи или задайте `LLM_MODEL` |
| `ModuleNotFoundError: src` | запуск не из корня репозитория | в workflow команда `python -m src.main` уже запускается из корня — проверьте, что `src/` лежит в корне |
