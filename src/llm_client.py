"""Универсальный клиент бесплатных LLM API с автоматическим фоллбэком в офлайн-движок."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from src.astro_engine import DailyAstroContext
from src.content_extras import LIBRA_TYPES, MONTH_THEMES
from src.fallback_writer import generate_fallback_post

ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "blockquote", "tg-spoiler", "a"}


def _detect_providers() -> list[dict[str, str]]:
    """Возвращает СПИСОК доступных бесплатных провайдеров в порядке приоритета.

    Каскад нужен для максимальной автономности: если первый провайдер вернул
    ошибку (лимит, сбой, отозванный ключ), код автоматически пробует следующий,
    и только в самом конце откатывается на офлайн-движок.
    """
    providers: list[dict[str, str]] = []

    explicit_key = os.getenv("LLM_API_KEY", "").strip()
    if explicit_key:
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
        providers.append({
            "name": "custom_llm",
            "url": f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url,
            "api_key": explicit_key,
            "model": model,
        })

    groq_key_early = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key_early:
        providers.append({
            "name": "groq_free",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "api_key": groq_key_early,
            "model": os.getenv("GROQ_MODEL", os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")).strip(),
        })

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        providers.append({
            "name": "gemini_free",
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "api_key": gemini_key,
            "model": os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", "gemini-2.5-flash")).strip(),
        })

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        providers.append({
            "name": "openrouter_free",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key": openrouter_key,
            "model": os.getenv("OPENROUTER_MODEL", os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")).strip(),
        })

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    if github_token:
        providers.append({
            "name": "github_models",
            "url": "https://models.github.ai/inference/chat/completions",
            "api_key": github_token,
            "model": os.getenv("GITHUB_MODEL", os.getenv("LLM_MODEL", "openai/gpt-4o-mini")).strip(),
        })

    return providers


def _detect_provider() -> dict[str, str] | None:
    """Первый доступный провайдер (совместимость с прежним кодом)."""
    providers = _detect_providers()
    return providers[0] if providers else None


def active_provider_label(force_offline: bool = False) -> str:
    """Человекочитаемое описание того, кто будет генерировать текст."""
    if force_offline:
        return "offline_engine (принудительно)"
    providers = _detect_providers()
    if not providers:
        return "offline_engine (ключи ИИ не заданы)"
    names = [f"{p['name']}:{p['model']}" for p in providers]
    return " → ".join(names) + " → offline_engine (резерв)"


def sanitize_telegram_html(text: str, max_len: int = 980) -> str:
    """Приводит текст к безопасному Telegram HTML и соблюдает лимит caption (1024)."""
    if not text:
        return ""

    # Конвертируем распространённые неподдерживаемые теги
    text = text.replace("<strong>", "<b>").replace("</strong>", "</b>")
    text = text.replace("<em>", "<i>").replace("</em>", "</i>")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(p|div|section|article|ul|ol|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)

    # Конвертируем случайный Markdown **жирный**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Экранируем одиночные '&', не являющиеся HTML-сущностями
    text = re.sub(r"&(?!amp;|lt;|gt;|quot;|#\d+;)", "&amp;", text)

    # Убираем любые теги кроме разрешённых Telegram
    def _filter_tag(match: re.Match[str]) -> str:
        full = match.group(0)
        is_close = full.startswith("</")
        tag_name = match.group(1).lower()
        if tag_name not in ALLOWED_TAGS:
            return ""
        if is_close:
            return f"</{tag_name}>"
        if tag_name == "a":
            href_m = re.search(r'href=["\']([^"\']+)["\']', full, flags=re.IGNORECASE)
            if href_m:
                return f'<a href="{href_m.group(1)}">'
            return ""
        return f"<{tag_name}>"

    text = re.sub(r"</?([a-zA-Z0-9-]+)(?:\s+[^>]*)?>", _filter_tag, text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # Укладываем в лимит caption, если передаётся с фото
    if len(text) > max_len:
        cut = text[: max_len - 1]
        # Пытаемся обрезать по границе абзаца или предложения
        last_nl = cut.rfind("\n")
        last_dot = cut.rfind(". ")
        split_at = max(last_nl, last_dot + 1 if last_dot > 0 else -1)
        if split_at > max_len * 0.55:
            cut = cut[:split_at].rstrip()
        else:
            cut = cut.rsplit(" ", 1)[0].rstrip() + "…"
        text = cut

    # Балансируем открытые теги
    stack: list[str] = []
    for m in re.finditer(r"<(/?)([a-zA-Z0-9-]+)(?:\s+[^>]*)?>", text):
        closing, tag = m.group(1), m.group(2).lower()
        if tag not in ALLOWED_TAGS:
            continue
        if not closing:
            stack.append(tag)
        else:
            if stack and stack[-1] == tag:
                stack.pop()
    while stack:
        text += f"</{stack.pop()}>"

    return text


def _build_prompts(ctx: DailyAstroContext, channel_handle: str) -> tuple[str, str]:
    system_prompt = (
        "Ты — главный редактор и опытный астролог-таролог премиального Telegram-канала для знака зодиака Весы (Libra). "
        "Тон канала: эстетичный, мистический, тёплый, вдохновляющий и психологически точный, без шаблонных фраз из жёлтых гороскопов. "
        "Формат ответа: строго JSON без Markdown-обёрток (```json не использовать), с ключами:\n"
        "- title: короткий заголовок для логов (до 60 символов)\n"
        "- card_headline: 2-4 слова ЗАГЛАВНЫМИ БУКВАМИ для обложки карточки (до 34 символов, без эмодзи)\n"
        "- card_subline: короткий подзаголовок на карточку (до 46 символов, без эмодзи)\n"
        "- post_html: готовый пост для Telegram в формате HTML (разрешены ТОЛЬКО теги <b>, <i>, <blockquote>), "
        "длиной строго от 520 до 860 символов (чтобы поместился под картинкой в Telegram!).\n"
        "В конце поста обязательно добавь короткий призыв поставить реакцию и хештеги."
    )

    rubric_instructions = {
        "forecast": (
            "Рубрика: Утренний астропрогноз дня для Весов. "
            "Дай цельный взгляд на день с учётом реальной Луны и её аспекта к Весам, "
            "выдели 3 коротких блока с эмодзи: общая атмосфера, дела/деньги, любовь/общение, и подсказку дня."
        ),
        "tarot": (
            f"Рубрика: Карта дня Таро для Весов. Выпала карта: «{ctx.tarot_card['numeral']}. {ctx.tarot_card['name']}» "
            f"(ключевые слова: {ctx.tarot_card['keywords']}). "
            f"Смысл для Весов: {ctx.tarot_card['libra_meaning']} Совет: {ctx.tarot_card['advice']}. "
            "Раскрой эту карту художественно, свяжи с энергией Венеры и сегодняшней Луной. "
            f"Для card_headline используй «{ctx.tarot_card['numeral']} • {ctx.tarot_card['name'].upper()}»."
        ),
        "love": (
            f"Рубрика: Любовь и совместимость дня. Сегодня в фокусе союз: Весы ♎ и {ctx.compat_partner['sign']} {ctx.compat_partner['symbol']}. "
            f"Базовая динамика: {ctx.compat_partner['dynamic']} "
            "Дай красивый разбор притяжения на сегодня как для пар, так и для свободных Весов. "
            f"Для card_headline используй «ВЕСЫ × {ctx.compat_partner['sign'].upper()}»."
        ),
        "venus": (
            "Рубрика: Совет Венеры и ритуал баланса. "
            "Напиши атмосферный пост-настрой с одной красивой эстетичной практикой на вечер/день и короткой аффирмацией в <blockquote>."
        ),
        "week_ahead": (
            "Рубрика: Фокус Весов на новую неделю. "
            "Помоги настроиться на ближайшие 7 дней: 3 коротких ориентира (энергия, дела, отношения) и счастливый ориентир."
        ),
        "sex": (
            f"Рубрика: Секс и чувственность Весов. Партнёрский знак дня — {ctx.compat_partner['sign']}. "
            "Пиши деликатно, эстетично, без пошлости и анатомических подробностей: речь о желании, близости, "
            "умении просить и слышать. Дай 3 блока: настроение дня, уровень желания (по шкале из 5), практика на вечер. "
            f"Для card_headline используй «ЧУВСТВЕННОСТЬ ВЕСОВ»."
        ),
        "love_daily": (
            f"Рубрика: Любовь с Весами, ежедневный разбор конкретной пары. Сегодня в фокусе: Весы ♎ × {ctx.compat_partner['sign']} {ctx.compat_partner['symbol']}. "
            f"Базовая динамика пары: {ctx.compat_partner['dynamic']} "
            "Дай 4 блока: как сегодня проявляется любовь, что нужно вашему человеку, баланс пары, часы для разговоров. "
            f"Для card_headline используй «ВЕСЫ × {ctx.compat_partner['sign'].upper()}»."
        ),
        "business": (
            f"Рубрика: Бизнес и деньги для Весов. Партнёрский знак дня — {ctx.compat_partner['sign']}. "
            "Дай 4 блока: фокус дня, партнёры и клиенты, деньги, индекс дел. "
            "Стиль деловой, но с астрологической ноткой, без обещаний дохода. "
            f"Для card_headline используй «БИЗНЕС ВЕСОВ»."
        ),
        "quiz": (
            f"Рубрика: Тест «Какой вы Весы?». Три типа: {', '.join(t['name'] for t in LIBRA_TYPES)}. "
            f"Тип дня — {ctx.libra_type['name'] if ctx.libra_type else LIBRA_TYPES[0]['name']}. "
            "Опиши три варианта по одной строке, попроси читателя написать цифру в комментариях, "
            "и раскрой тип дня: сильная сторона, риск, совет."
        ),
        "moon_today": (
            "Рубрика: Луна сегодня. Это КОРОТКАЯ карточка без длинного текста: фаза Луны, знак, "
            "освещённость, одна ёмкая фраза-послание дня и приглашение переслать пост. "
            "Максимум 420 символов. Никаких списков и разборов."
        ),
        "month_love": (
            f"Рубрика: ЛЮБОВЬ ВЕСОВ НА {ctx.target_month_name.upper()} — прогноз на следующий месяц. "
            f"Тема месяца: {MONTH_THEMES[ctx.target_month % len(MONTH_THEMES)]}. "
            "Дай масштабный, но конкретный прогноз на месяц: главная линия, удачные дни, что отпустить."
        ),
        "month_sex": (
            f"Рубрика: ЧУВСТВЕННОСТЬ ВЕСОВ НА {ctx.target_month_name.upper()} — прогноз на месяц. "
            "Деликатно и эстетично: главная линия желания, практика месяца, лучшие дни."
        ),
        "month_business": (
            f"Рубрика: БИЗНЕС ВЕСОВ НА {ctx.target_month_name.upper()} — прогноз на месяц. "
            "Главная линия в делах и деньгах, партнёрства, удачные дни для сделок."
        ),
    }

    handle_note = f"В самом конце добавь теги {ctx.rubric_hashtag} • {channel_handle}" if channel_handle else f"В конце добавь теги {ctx.rubric_hashtag}"

    user_prompt = (
        f"Сегодня: {ctx.date_human} ({ctx.weekday_name}), планета дня — {ctx.planet_ruler} ({ctx.planet_theme}).\n"
        f"Астрономические данные:\n"
        f"- Солнце в знаке: {ctx.sun_sign} ({ctx.sun_degree}°)\n"
        f"- Луна в знаке: {ctx.moon_sign} ({ctx.moon_degree}°, стихия {ctx.moon_element})\n"
        f"- Фаза Луны: {ctx.moon_phase_name}, освещённость {ctx.moon_illumination}%, {ctx.lunar_day}-й лунный день\n"
        f"- Аспект к Весам: {ctx.libra_aspect} ({ctx.libra_aspect_tone})\n"
        f"- Индексы (из 5): Любовь {ctx.love_score}/5, Дела {ctx.career_score}/5, Энергия {ctx.energy_score}/5\n"
        f"- Ориентиры: цвет «{ctx.lucky_color}», камень «{ctx.lucky_stone}», число {ctx.lucky_number}, часы удачи {ctx.lucky_hours}\n\n"
        f"{rubric_instructions.get(ctx.rubric_key, rubric_instructions['forecast'])}\n"
        f"{handle_note}"
    )
    return system_prompt, user_prompt


def _extract_json_payload(raw_content: str) -> dict[str, Any]:
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    data = json.loads(cleaned)
    if not isinstance(data, dict) or "post_html" not in data:
        raise ValueError("JSON не содержит post_html")
    return data


def _request_llm(provider: dict[str, str], system_prompt: str, user_prompt: str) -> str:
    """Один запрос к провайдеру. Возвращает сырой текст ответа модели."""
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    if provider["name"] == "openrouter_free":
        headers["HTTP-Referer"] = "https://github.com/libra-content-factory"
        headers["X-Title"] = "Libra Content Factory"

    payload = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 900,
    }

    resp = requests.post(provider["url"], headers=headers, json=payload, timeout=45)
    if resp.status_code != 200:
        detail = resp.text[:200].replace("\n", " ")
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
    body = resp.json()
    return body["choices"][0]["message"]["content"]


def generate_post_content(
    ctx: DailyAstroContext,
    channel_handle: str = "",
    force_offline: bool = False,
) -> dict[str, Any]:
    """Генерирует пост через бесплатные LLM API с каскадом провайдеров и офлайн-резервом."""
    fallback = generate_fallback_post(ctx, channel_handle=channel_handle)
    if force_offline:
        return fallback

    providers = _detect_providers()
    if not providers:
        return fallback

    system_prompt, user_prompt = _build_prompts(ctx, channel_handle=channel_handle)
    attempts: list[str] = []

    for provider in providers:
        label = f"{provider['name']}:{provider['model']}"
        try:
            raw_text = _request_llm(provider, system_prompt, user_prompt)
            parsed = _extract_json_payload(raw_text)

            post_html = sanitize_telegram_html(str(parsed.get("post_html", "")), max_len=980)
            if len(post_html) < 120:
                raise ValueError("Слишком короткий ответ LLM")

            headline = re.sub(r"[<>]", "", str(parsed.get("card_headline") or fallback["card_headline"])).strip()[:38]
            subline = re.sub(r"[<>]", "", str(parsed.get("card_subline") or fallback["card_subline"])).strip()[:52]
            title = str(parsed.get("title") or fallback["title"]).strip()[:100]

            return {
                "title": title,
                "card_headline": headline.upper(),
                "card_subline": subline,
                "post_html": post_html,
                "source": label,
                "provider_attempts": attempts + [f"{label}: ok"],
            }
        except Exception as exc:  # noqa: BLE001 — пробуем следующего провайдера
            attempts.append(f"{label}: {type(exc).__name__}: {exc}")
            continue

    fallback["fallback_reason"] = " | ".join(attempts) if attempts else "нет доступных провайдеров"
    fallback["provider_attempts"] = attempts
    return fallback
