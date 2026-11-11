# ⚖️ Бесплатный контент-завод для Telegram-канала «Весы»

Полностью автономная система ежедневной генерации и публикации постов с брендированными Таро-карточками в стиле вашей аватарки (`assets/libra_avatar.png`).

**Стоимость работы: 0 ₽/мес** — не нужен VPS-сервер и не нужны платные подписки:
1. **Облачный планировщик:** GitHub Actions (бесплатный cron-запуск каждый день).
2. **Точная астрономия без API:** встроенный математический движок (`src/astro_engine.py`) по формулам Жана Меёса сам вычисляет реальный знак Солнца, знак Луны, фазу Луны, процент освещённости, лунный день и аспект к знаку Весы.
3. **Бесплатный ИИ на выбор (плюс офлайн-движок):**
   - **GitHub Models** (работает прямо через `GITHUB_TOKEN` в GitHub Actions — без регистрации отдельных ключей!),
   - или **Google Gemini API** (бесплатный тариф в Google AI Studio),
   - или **Groq / OpenRouter `:free`** (бесплатные квоты без карты),
   - **+ умный офлайн-генератор** (`src/fallback_writer.py`), который сработает автоматически, если не задан ни один ключ или лимит API исчерпан.
4. **Авто-генерация картинок (`1080×1350`):** `src/card_generator.py` на Python + Pillow рисует винтажные Таро-карточки в цветах аватарки канала и отображает на них **реальную сегодняшнюю фазу Луны**.
5. **Антиповтор тем:** история выпавших карт Таро и знаков совместимости сохраняется в `data/history.json`.

---

## 📁 Структура проекта

```text
libra-content-factory/
├── .github/workflows/autopost.yml  # Расписание автопубликации в GitHub Actions
├── assets/libra_avatar.png         # Аватарка вашего канала
├── data/history.json               # Антиповтор карт Таро и совместимости
├── src/
│   ├── astro_engine.py             # Расчёт фазы Луны, знаков, аспектов к Весам и рубрик
│   ├── card_generator.py           # Рендер 1080x1350 PNG-карточек в стиле Таро/золото
│   ├── llm_client.py               # Клиент бесплатных LLM + защита Telegram HTML
│   ├── fallback_writer.py          # Резервный офлайн-генератор постов
│   ├── telegram_publisher.py       # Отправка в Telegram (авто или черновик админу)
│   └── main.py                     # Точка входа
├── templates/content_plan.md       # Контент-стратегия и рубрикатор
├── tests/test_factory.py           # Автотесты
├── .env.example                    # Пример переменных окружения
└── requirements.txt                # requests и pillow
```

---

## 🚀 Запуск за 10 минут (бесплатно в облаке GitHub)

### Шаг 1. Создайте Telegram-бота
1. Откройте [@BotFather](https://t.me/BotFather) и отправьте `/newbot`.
2. Придумайте имя и юзернейм бота (например, `vesy_autopost_bot`).
3. Скопируйте выданный **токен** — это ваш `TG_BOT_TOKEN`.
4. Добавьте этого бота **администратором** в ваш Telegram-канал (дайте право публиковать сообщения и медиа).
5. Узнайте ID канала:
   - если канал публичный — укажите `@username_вашего_канала`,
   - если закрытый — перешлите любое сообщение из канала в [@userinfobot](https://t.me/userinfobot) или [@getidsbot](https://t.me/getidsbot) и возьмите ID вида `-1001234567890`.

> 🛠️ **Загрузили файлы «плоско» и запуск упал с `No file matched to **/requirements.txt`?**
> Готовая починка структуры — [`templates/FIX_STRUCTURE.md`](templates/FIX_STRUCTURE.md)

> 📖 **Нужна детальная пошаговая инструкция с картинками-подсказками, скриншот-путями, решениями частых ошибок и готовым `.zip`-архивом проекта?** Откройте [`templates/GITHUB_SETUP.md`](templates/GITHUB_SETUP.md).

### Шаг 2. Загрузите папку `libra-content-factory` на GitHub
1. Зарегистрируйтесь или войдите на [GitHub](https://github.com) и создайте новый репозиторий (можно **Private** — 2000 бесплатных минут Actions в месяц хватит с огромным запасом, наш скрипт тратит ~15 минут в месяц).
2. Загрузите содержимое папки `libra-content-factory` в корень репозитория (включая скрытую папку `.github/workflows/autopost.yml`).

### Шаг 3. Добавьте секреты в GitHub

> 🔐 **Подробный разбор этого шага** — [`templates/SECRETS.md`](templates/SECRETS.md): где находится раздел, форматы значений, 3 способа узнать ID канала, таблица всех ошибок и как их исправить.

Путь: **Settings → Secrets and variables → Actions** (именно в настройках репозитория, а не в верхней вкладке «Actions»!).

**(а) Вкладка Secrets → New repository secret**

| Имя | Обязательно | Значение |
|---|---|---|
| `TG_BOT_TOKEN` | ✅ | токен от [@BotFather](https://t.me/BotFather) вида `1234567890:AAF…` |
| `TG_CHANNEL_ID` | ✅ | `@username_канала` или числовой `-1001234567890` |
| `TG_ADMIN_ID` | только для `draft` | ваш chat_id от [@userinfobot](https://t.me/userinfobot) |
| `GEMINI_API_KEY` | по желанию | бесплатный ключ [Google AI Studio](https://aistudio.google.com/apikey) |
| `GROQ_API_KEY` | по желанию | бесплатный ключ [Groq Console](https://console.groq.com/keys) |
| `OPENROUTER_API_KEY` | по желанию | бесплатный ключ [OpenRouter](https://openrouter.ai/keys) |

> Ключи ИИ нужны максимум один — при отсутствии всех завод работает на встроенном офлайн-генераторе. `GITHUB_TOKEN` GitHub выдаёт автоматически, добавлять вручную не нужно.

**(б) Вкладка Variables → New repository variable** (несекретные настройки)

| Имя | По умолчанию | Зачем |
|---|---|---|
| `CHANNEL_HANDLE` | `@vesy_prognoz` | подпись на карточке и в конце поста — укажите ваш канал |
| `PUBLISH_MODE` | `auto` | `auto` — сразу в канал, `draft` — черновик вам в личку |
| `TIMEZONE_OFFSET` | `3` | часовой пояс (Москва = 3) |

**(в) Проверка настроек без публикации** (если не видите кнопку — см. [`templates/ACTIONS_BUTTON.md`](templates/ACTIONS_BUTTON.md)): вкладка **Actions → Check Setup (diagnostics) → Run workflow**. Появится отчёт: найден ли бот, виден ли канал, есть ли у бота право публикации, какой провайдер ИИ активен. Локально то же самое: `python -m tools.preflight --test-llm`.

### Шаг 4. Первый тестовый запуск
1. Перейдите на вкладку **Actions** в вашем репозитории на GitHub.
2. Выберите **Libra Content Factory Autopost → Run workflow**.
3. Поставьте `dry_run: true`, нажмите **Run workflow** — в разделе **Artifacts** можно скачать и посмотреть готовую карточку.
4. Затем запустите с `dry_run: false` — первый пост с картинкой мгновенно появится в вашем Telegram-канале!
5. Далее всё будет публиковаться автоматически: **в 08:30 МСК** (прогноз) и **в 19:00 МСК** (Таро / Любовь / Совет Венеры). Чтобы оставить 1 пост в день, удалите вторую строчку `cron` в `.github/workflows/autopost.yml`.

---

## 💻 Локальный запуск на своём компьютере (для проверки)

```bash
pip install -r requirements.txt
cp .env.example .env
# Тестовая генерация прогноза без отправки в Telegram:
python -m src.main --slot morning --dry-run
# Тестовая генерация карты Таро дня:
python -m src.main --slot tarot --dry-run
```
Готовые файлы появятся в папке `output/`.
