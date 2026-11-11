# 🔁 Замена подписи `@vesy_prognoz` → `@libra_astra`

## Почему не сработало

В вашем репозитории файлы остались старыми:

```yaml
# .github/workflows/autopost.yml (строка 137)
CHANNEL_HANDLE: ${{ vars.CHANNEL_HANDLE || '@vesy_prognoz' }}
```

Workflow читает подпись **только из вкладки Variables**. Если вы добавили `CHANNEL_HANDLE`
во вкладку **Secrets**, переменная не подхватилась — и включился жёсткий дефолт `@vesy_prognoz`.
В `src/main.py` тоже был старый дефолт: `os.getenv("CHANNEL_HANDLE", "@vesy_prognoz")`.

## Что исправлено (двойная защита)

```yaml
# теперь читаются ОБА источника, а дефолт — правильный
CHANNEL_HANDLE: ${{ vars.CHANNEL_HANDLE || secrets.CHANNEL_HANDLE || '@libra_astra' }}
```

```python
# src/main.py
channel_handle = os.getenv("CHANNEL_HANDLE", "@libra_astra").strip()
```

И добавилась строка в лог, чтобы было видно, какое значение реально попало в рендер:

```
::notice::Подпись канала (CHANNEL_HANDLE): '@libra_astra'
[2/5] Генерация текста: провайдер=offline, подпись='@libra_astra'
```

---

## Вариант 1 (самый простой): ничего не менять в GitHub

Просто **перезапишите `autopost.yml`** файлом `/home/user/upload-files/autopost.yml`.
В нём дефолт уже `@libra_astra` — подпись исправится даже без переменной.

1. `https://github.com/andrey9653246431-spec/Libra_content_factory/blob/main/.github/workflows/autopost.yml`
2. ✏️ **Edit this file** → **Ctrl+A** → **Delete** → вставить содержимое `upload-files/autopost.yml`
3. **Commit changes**
4. **Actions → Libra Content Factory Autopost → Run workflow** (`dry_run: false`)

> Правка `.github/workflows/…` автоматически запустит workflow в режиме `dry_run` — пост не уйдёт,
> это безопасно. После этого сделайте ручной запуск.

## Вариант 2: добавить переменную в правильную вкладку

**Settings → Secrets and variables → Actions → вкладка `Variables`** (НЕ Secrets)

| Name | Value |
|---|---|
| `CHANNEL_HANDLE` | `@libra_astra` |

> Если `CHANNEL_HANDLE` вы создали в **Secrets** — теперь это тоже работает (после обновления workflow),
> но лучше держать подпись в Variables: это не секрет.

## Вариант 3: убрать старое значение из Secrets

Если в Secrets лежит `CHANNEL_HANDLE=@vesy_prognoz`, то после обновления workflow
именно оно может перебить дефолт (порядок: Variables → Secrets → дефолт).

**Settings → Secrets and variables → Actions → Secrets → `CHANNEL_HANDLE` → Delete**
(и при необходимости создать его в Variables со значением `@libra_astra`).

---

## Как проверить, что подпись применилась

В логе запуска появится строка:

```
::notice::Подпись канала (CHANNEL_HANDLE): '@libra_astra'
```

и на карточке внизу, а также в последней строке поста будет `@libra_astra`:

```
#КартаДняВесы #ТароДляВесов • @libra_astra
```

## Проверено локально

| Сценарий | Результат |
|---|---|
| переменная не задана | `подпись='@libra_astra'`, в посте `• @libra_astra` |
| `CHANNEL_HANDLE=@libra_astra` | `подпись='@libra_astra'`, в посте `• @libra_astra` |
| юнит-тесты | `Ran 5 tests … OK` |

## Файлы

- `/home/user/upload-files/autopost.yml` — обновлённый workflow
- `/home/user/upload-files/main.py` — обновлённый код (дефолт + лог подписи)
- `/home/user/libra-content-factory.zip` — весь проект со всеми правками
