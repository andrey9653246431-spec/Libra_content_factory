# 🧯 Разбор: «push не удался» + exit code 1 в шаге публикации

## Что показал лог

```
step:3:39  Структура нарушена — распаковываю libra-content-factory.zip     ✅ архив найден и распакован
step:3:74  push не удался — структура исправлена только на время запуска   ⚠️ коммит не ушёл в ветку
step:3:75  Структура восстановлена из архива                               ✅ в раннере файлы на местах
step:7:60  Process completed with exit code 1                              ❌ упал шаг публикации
```

## Причина №1: почему `git push` отклонён

GitHub защищает файлы workflow. Ошибка выглядит так:

```
refusing to allow a GitHub App to create or update workflow
`.github/workflows/autopost.yml` without `workflows` permission
```

`GITHUB_TOKEN` внутри Actions **не имеет** права `workflows`, а шаг `Bootstrap` распаковывал архив
**вместе с `.github/workflows/`** → пытался закоммитить изменённый workflow → push отклонялся.
Из-за этого структура чинилась только «на время запуска», и в репозитории оставалась старая раскладка.

**Исправлено:** перед коммитом папка `.github/workflows` возвращается к версии из репозитория:

```bash
git checkout -- .github/workflows || true
git clean -fdq .github/workflows || true
```

Теперь коммитятся только `src/`, `data/`, `tests/`, `assets/`, `templates/`, `tools/`,
`requirements.txt`, `README.md` и удаление архива — а это `GITHUB_TOKEN` менять может.

> Кстати, `permissions: workflow` в GitHub Actions не существует — добавить его нельзя,
> поэтому единственный рабочий путь именно такой.

## Причина №2: почему шаг публикации упал

`Bootstrap` восстановил файлы, но **секреты не связаны с кодом**: если `TG_BOT_TOKEN`
не задан (или задан с другим именем), `publish_to_telegram()` бросает `ValueError`,
и запуск завершается `exit code 1`.

Проверьте: **Settings → Secrets and variables → Actions → вкладка Secrets**.
Там должны быть ровно два имени:

| Имя секрета | Пример значения |
|---|---|
| `TG_BOT_TOKEN` | `7891234567:AAF7xQwErTy…` |
| `TG_CHANNEL_ID` | `@libra_astra` или `-1001234567890` |

Частые ошибки:

- секрет добавлен во вкладку **Variables** (не Secrets) — в `secrets.*` он не попадёт;
- имя с опечаткой: `TG_TOKEN`, `TELEGRAM_BOT_TOKEN`, `BOT_TOKEN`;
- значение с кавычками или пробелами: `"@libra_astra"`;
- канал закрытый, а указан `@username` — нужен числовой `-100…`;
- бот не добавлен администратором канала с правом «Публикация сообщений».

**Исправлено:** `src/main.py` больше не падает «голым» traceback, а печатает понятный отчёт:

```
==============================================================
❌ ГЕНЕРАЦИЯ/ПУБЛИКАЦИЯ НЕ УДАЛАСЬ
   ValueError: Не задан TG_BOT_TOKEN
--------------------------------------------------------------
   Причина: не заданы переменные окружения/секреты:
     • TG_BOT_TOKEN
     • TG_CHANNEL_ID
   Где добавить: Settings → Secrets and variables → Actions → Secrets
   Затем: Actions → Check Setup (diagnostics) → Run workflow
==============================================================
```

## Что сделать сейчас (три шага)

### Шаг 1. Перезапишите два файла

| Файл в репозитории | Откуда взять |
|---|---|
| `.github/workflows/autopost.yml` | `/home/user/upload-files/autopost.yml` |
| `src/main.py` | `/home/user/upload-files/main.py` |

> `src/main.py` в вашем репозитории отсутствует (структура ещё «плоская»), поэтому:
> **Add file → Create new file** → имя `src/main.py` → вставить содержимое → Commit.

Как перезаписать `autopost.yml`: откройте файл в GitHub → ✏️ **Edit this file** → **Ctrl+A** → вставьте новое содержимое → **Commit changes**.

### Шаг 2. Проверьте секреты

**Settings → Secrets and variables → Actions → Secrets** — должны быть `TG_BOT_TOKEN` и `TG_CHANNEL_ID`.
Если сомневаетесь в правильности — прогоните диагностику: **Actions → Check Setup (diagnostics) → Run workflow**
(файл `check-setup.yml` возьмите из `/home/user/upload-files/check-setup.yml`, если его ещё нет в репозитории).

### Шаг 3. Запустите

**Actions → Libra Content Factory Autopost → Run workflow**, `dry_run: true`.

- Сначала пройдёт `Bootstrap` — и теперь `push` должен завершиться **успешно**
  (`::notice::Структура зафиксирована в репозитории`).
- `Verify repository layout` покажет ✅ по всем файлам.
- `Generate and publish post` с `dry_run: true` **ничего не отправляет** и не требует секретов.

Когда в логе всё зелёное — повторите запуск с `dry_run: false`, и пост уйдёт в канал.

## Как понять, что запуск удался: ожидаемый лог

```
Bootstrap layout from zip (if repo is not laid out)
  ::warning::Структура нарушена — распаковываю libra-content-factory.zip
  ::notice::Структура зафиксирована в репозитории

Verify repository layout
  ✅ requirements.txt
  ✅ src/main.py
  ✅ src/astro_engine.py
  ✅ src/card_generator.py
  ✅ src/llm_client.py
  ✅ src/fallback_writer.py
  ✅ src/telegram_publisher.py

Generate and publish post
  [OK] Дата: 2026-11-11 | Рубрика: forecast | Источник: offline_engine
  [OK] Заголовок: Астропрогноз для Весов на 11 ноября
  [OK] Карточка: /home/runner/work/.../output/card_2026-11-11_forecast.png
  [OK] Опубликовано в Telegram: False

Save generated preview artifacts → Artifact «libra-post-preview» готов к скачиванию
```

## Если снова упадёт — пришлите одну строку

В логе шага **Generate and publish post** найдите строку после
`❌ ГЕНЕРАЦИЯ/ПУБЛИКАЦИЯ НЕ УДАЛАСЬ` — там будет либо `ValueError: Не задан TG_BOT_TOKEN`,
либо `Telegram API error (400/403): …`. По ней я точно скажу, что править.

## Уведомление про Ubuntu — это не ошибка

`The ubuntu-latest label will migrate to Ubuntu 26` — информационное сообщение GitHub,
на работу не влияет. `Node.js 20 deprecated` тоже убрано: в актуальном `autopost.yml`
используются `actions/checkout@v6`, `actions/setup-python@v6`, `actions/upload-artifact@v6`.
