# 🔎 Шаг 7 падает: как узнать точную причину за 30 секунд

## Что известно

```
✅ 3  Bootstrap layout from zip           «Структура репозитория в порядке»
✅ 4  Verify repository layout
✅ 5  Setup Python
✅ 6  Install fonts and Python deps
❌ 7  Generate and publish post           exit code 1   ← за 1 секунду
⏭️ 8  Save generated preview artifacts    skipped
⏭️ 9  Commit updated anti-repeat history  skipped
```

Структура и зависимости в порядке. Шаг 7 упал **до рендера карточки** (1 секунда):
код ушёл в `publish_to_telegram()` и получил ответ от Telegram, либо не нашёл секреты.

Возможных причин ровно четыре — и каждая теперь печатает свою строку в логе.

---

## Что делать (3 шага)

### Шаг 1. Обновите два файла

| Файл в репозитории | Откуда |
|---|---|
| `.github/workflows/autopost.yml` | `/home/user/upload-files/autopost.yml` |
| `src/main.py` | `/home/user/upload-files/main.py` |

> В новой версии добавлен `--verbose` и `VERBOSE: "1"` — теперь в логе видно
> номер этапа, длину подписи и **ответ Telegram API целиком**.

### Шаг 2. Запустите с `dry_run: true`

**Actions → Libra Content Factory Autopost → Run workflow** → `slot: auto`, `dry_run: **true**`.

С `dry_run` публикация вообще не вызывается. Если такой запуск **зелёный** — значит
проблема ровно в секретах/правах, а не в коде.

### Шаг 3. Запустите с `dry_run: false` и прочитайте лог

В шаге `Generate and publish post` появится:

```
::notice::Запуск: slot=auto dry_run=False token_set=True channel_set=True
[1/5] Расчёт астроданых: слот=morning, дата=2026-11-11
[2/5] Генерация текста: провайдер=auto
[3/5] Рендер карточки: forecast
[4/5] Публикация: channel='@vesy_prognoz', mode='auto', token=задан, caption_len=622
==============================================================
❌ ГЕНЕРАЦИЯ/ПУБЛИКАЦИЯ НЕ УДАЛАСЬ
   RuntimeError: Telegram API error (<код>): <описание>
==============================================================
```

---

## Расшифровка кода ошибки Telegram

| Что в логе | Причина | Что сделать |
|---|---|---|
| `Не заданы секреты: TG_BOT_TOKEN` | секрет не создан / другое имя / лежит во вкладке **Variables** | **Settings → Secrets and variables → Actions → Secrets** → `TG_BOT_TOKEN` |
| `Не заданы секреты: TG_CHANNEL_ID` | см. ниже: можно заменить на `CHANNEL_HANDLE` | добавить `TG_CHANNEL_ID` **или** Variables `CHANNEL_HANDLE=@ваш_канал` |
| `(401): Unauthorized` | токен скопирован не полностью, отозван или от другого бота | @BotFather → `/mybots` → ваш бот → **API Token**; проверить в браузере `https://api.telegram.org/bot<ТОКЕН>/getMe` |
| `(400): chat not found` | бот не в канале, неверный `@username`, или для закрытого канала указан username вместо `-100…` | добавить бота **администратором** канала; для закрытого — числовой id (`@getidsbot`) |
| `(403): bot is not a member of the channel chat` | бот удалён из канала или не админ | «Управление каналом → Администраторы → Добавить администратора» |
| `(403): not enough rights to send photos` | у бота нет права **«Публикация сообщений»** | включить галочку «Post messages» в правах бота |
| `(400): wrong file identifier / PHOTO_INVALID_DIMENSIONS` | битый PNG (крайне редко) | запустить с `--no-image` один раз и сообщить мне |
| `(400): Bad Request: can't parse entities` | в тексте попал HTML-тег, не поддержанный Telegram | сообщить мне — добавлю тег в sanitizer |

---

## Важное упрощение: `CHANNEL_HANDLE` теперь может заменить `TG_CHANNEL_ID`

Если канал публичный (есть ссылка `t.me/...`), достаточно:

1. **Variables** → `CHANNEL_HANDLE` = `@ваш_канал`
2. **Secrets** → только `TG_BOT_TOKEN`

Код сам подставит `CHANNEL_HANDLE` в `TG_CHANNEL_ID`. В логе это видно:
`channel='@ваш_канал'`.

---

## Проверка «до похода в GitHub»: локально

```bash
cd libra-content-factory
pip install -r requirements.txt

# 1) генерация без публикации
python -m src.main --slot forecast --dry-run --offline --verbose

# 2) проверка секретов и прав бота (нужен рабочий токен)
export TG_BOT_TOKEN="7891234567:AAF…"
export TG_CHANNEL_ID="@ваш_канал"
python -m tools.preflight --test-llm
```

`preflight` покажет точную причину (бот найден / канал найден / права / ИИ) и вернёт
код 1, если что-то не так.

---

## Что уже проверено в этой версии

- без секретов: `❌ Не заданы секреты: TG_BOT_TOKEN, TG_CHANNEL_ID` + `::error::` и код возврата 1;
- `--dry-run --verbose`: полный лог `[1/5]…[3/5]`, карточка создаётся, публикация пропускается;
- неверный токен: `RuntimeError: Telegram API error (401): Unauthorized` — без «голого» traceback;
- только `TG_BOT_TOKEN` + `CHANNEL_HANDLE=@channel`: `channel='@channel'`, публикация пытается выполниться;
- юнит-тесты: `Ran 5 tests … OK`.
