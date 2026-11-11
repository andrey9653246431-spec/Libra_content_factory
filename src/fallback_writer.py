"""Резервный офлайн-генератор постов для Весов (работает на 100% бесплатно без LLM API)."""

from __future__ import annotations

import hashlib
from typing import Any

from src.astro_engine import DailyAstroContext

PHASE_GUIDANCE = {
    "new": "Время тихих намерений: не спешите с громкими обещаниями, лучше наметьте главный вектор на месяц.",
    "waxing_crescent": "Первые ростки идей просят бережного внимания. Хорошо делать первые лёгкие шаги и знакомиться.",
    "first_quarter": "День просит ясности и смелого выбора: Весам важно не зависать в сомнениях.",
    "waxing_gibbous": "Энергия набирает силу — доводите начатые разговоры и проекты до красивой формы.",
    "full": "Эмоции звучат громче обычного. Ищите внутренний центр и не поддавайтесь чужой суете.",
    "waning_gibbous": "Хороший период для благодарности, подведения промежуточных итогов и тёплой отдачи.",
    "last_quarter": "Освободитесь от лишних обязательств и недосказанностей, которые тянут энергию.",
    "waning_crescent": "Замедляйтесь и берегите ресурс: тишина и эстетичный отдых дадут больше пользы, чем гонка.",
}

ELEMENT_NOTES = {
    "Воздух": "Луна в родственной стихии Воздуха ускоряет диалоги, приносит нужных людей и свежий взгляд на старую задачу.",
    "Огонь": "Огненная Луна добавляет смелости и харизмы — сегодня легче проявить инициативу и очаровать собеседников.",
    "Земля": "Земная Луна заземляет воздушную натуру Весов: отличный момент навести порядок в финансах, делах и планах.",
    "Вода": "Водная Луна усиливает интуицию и тонкое чутьё — прислушивайтесь к подтексту и не игнорируйте настроение.",
}

LOVE_FORECASTS = [
    "В отношениях ценится искренний диалог без намёков: одно тёплое сообщение разрядит любое напряжение.",
    "Притягательность Весов сегодня работает мягко, но безотказно — позвольте себе чуть больше флирта и открытости.",
    "Если в паре накопился мелкий вопрос, обсудите его за красивым ужином — атмосфера решает половину дела.",
    "Свободным Весам звёзды советуют не сидеть дома: случайная переписка или встреча может оказаться многообещающей.",
]

CAREER_FORECASTS = [
    "Ваша сильная сторона сегодня — дипломатия: вы сможете договориться даже там, где другие зашли в тупик.",
    "Не берите на себя чужую рутину из вежливости. Выберите 1–2 ключевые задачи и доведите их до блеска.",
    "Хорошее время для переговоров, оформления проектов, эстетики и всего, где важен ваш безупречный вкус.",
    "Финансовые решения принимайте с холодной головой: сравните варианты, прежде чем тратить импульсивно.",
]

VENUS_RITUALS = [
    "Сделайте маленькую «паузу Венеры»: зажгите свечу, уберите визуальный шум на столе и выберите одну вещь, за которую благодарны себе сегодня.",
    "Ваша стихия — воздух и гармония: откройте окно на 5 минут, включите любимый трек и спросите себя: «Чего хочу именно я, а не из чувства долга?»",
    "Баланс начинается с тела: тёплая вода, любимый аромат и спокойный вечер без лишних новостей восстановят ресурс быстрее любых советов.",
    "Весы расцветают в красоте: наденьте завтра деталь цвета «{color}» и не извиняйтесь за желание окружать себя эстетикой.",
]

ENGAGEMENT_CTAS = [
    "Как откликается день? Оставьте 🔥, если чувствуете прилив сил, или 🌙 — если хочется тишины и отдыха.",
    "Проверяем баланс Весов: что сегодня на первом месте — дела (💼) или чувства (❤️)?",
    "Ставьте ✨, если забираете этот прогноз себе, и делитесь в комментариях своим настроением дня!",
    "Откликается карта? Нажмите ❤️, чтобы закрепить удачную волну на сегодня.",
]


def _pick(items: list[str], seed: str) -> str:
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return items[int.from_bytes(h[:4], "big") % len(items)]


def _stars(score: int) -> str:
    return "★" * score + "☆" * (5 - score)


def generate_fallback_post(ctx: DailyAstroContext, channel_handle: str = "") -> dict[str, Any]:
    """Создаёт готовый структурированный пост и текст карточки без участия LLM."""
    seed_base = f"{ctx.date_iso}-{ctx.slot}-{ctx.rubric_key}"
    phase_tip = PHASE_GUIDANCE.get(ctx.moon_phase_key, "")
    element_tip = ELEMENT_NOTES.get(ctx.moon_element, "")
    cta = _pick(ENGAGEMENT_CTAS, seed_base + "-cta")
    footer = f"\n\n{ctx.rubric_hashtag}" + (f" • {channel_handle}" if channel_handle else "")

    if ctx.rubric_key == "tarot":
        card = ctx.tarot_card
        title = f"Карта дня: {card['numeral']} • {card['name']}"
        card_headline = f"{card['numeral']} • {card['name'].upper()}"
        card_subline = card["keywords"]
        post_html = (
            f"🃏 <b>КАРТА ДНЯ ДЛЯ ВЕСОВ — {ctx.date_human.upper()}</b>\n"
            f"<i>{ctx.weekday_name} • Луна в {ctx.moon_sign_locative} ({ctx.moon_phase_name})</i>\n\n"
            f"✨ Аркан дня: <b>{card['numeral']}. {card['name']}</b>\n"
            f"<blockquote>{card['keywords']}</blockquote>\n\n"
            f"⚖️ <b>Что это значит для Весов:</b>\n{card['libra_meaning']}\n\n"
            f"🗝 <b>Совет карты:</b> {card['advice']}\n\n"
            f"🔮 <b>Фокус дня:</b> цвет — <i>{ctx.lucky_color}</i>, камень — <i>{ctx.lucky_stone}</i>.\n\n"
            f"{cta}{footer}"
        )

    elif ctx.rubric_key == "love":
        partner = ctx.compat_partner
        love_tip = _pick(LOVE_FORECASTS, seed_base + "-love")
        title = f"Весы и {partner['sign']}: притяжение дня"
        card_headline = f"ВЕСЫ ♎ × {partner['sign'].upper()} {partner['symbol']}"
        card_subline = "Любовь • Гармония • Диалог"
        post_html = (
            f"✨ <b>ЛЮБОВЬ И СОВМЕСТИМОСТЬ — {ctx.date_human.upper()}</b>\n"
            f"<i>День под знаком: Весы ♎ и {partner['sign']} {partner['symbol']}</i>\n\n"
            f"💞 <b>Динамика пары:</b>\n{partner['dynamic']}\n\n"
            f"🌙 <b>Настроение Венеры:</b>\n{love_tip} {element_tip}\n\n"
            f"⚖️ <b>Индекс притяжения:</b> {_stars(ctx.love_score)}\n"
            f"⏰ <b>Удачные часы для свидания и разговоров:</b> {ctx.lucky_hours}\n\n"
            f"{cta}{footer}"
        )

    elif ctx.rubric_key == "venus":
        ritual = _pick(VENUS_RITUALS, seed_base + "-ritual").format(color=ctx.lucky_color)
        title = f"Совет Венеры на {ctx.date_human}"
        card_headline = "РИТУАЛ РАВНОВЕСИЯ"
        card_subline = f"Венера • {ctx.lunar_day}-й лунный день"
        post_html = (
            f"🌙 <b>СОВЕТ ВЕНЕРЫ ДЛЯ ВЕСОВ — {ctx.date_human.upper()}</b>\n"
            f"<i>{ctx.lunar_day}-й лунный день • {ctx.moon_phase_name}</i>\n\n"
            f"🕊 <b>Настрой дня:</b>\n{phase_tip}\n\n"
            f"✨ <b>Практика для внутреннего баланса:</b>\n{ritual}\n\n"
            f"<blockquote>«Моя красота и сила рождаются там, где я выбираю спокойную ясность вместо сомнений.»</blockquote>\n\n"
            f"{cta}{footer}"
        )

    elif ctx.rubric_key == "week_ahead":
        title = "Фокус Весов на новую неделю"
        card_headline = "НАСТРОЙКА НА НЕДЕЛЮ"
        card_subline = f"{ctx.moon_phase_name} • Луна в {ctx.moon_sign_locative}"
        post_html = (
            f"🔮 <b>ФОКУС ВЕСОВ НА НОВУЮ НЕДЕЛЮ</b>\n"
            f"<i>{ctx.date_human} • {ctx.moon_phase_name} ({ctx.moon_illumination}%)</i>\n\n"
            f"⚖️ <b>Главный вектор:</b>\n{ctx.libra_aspect} открывает неделю с акцентом на {ctx.libra_aspect_tone}.\n\n"
            f"🌿 <b>Что важно сделать:</b>\n"
            f"• Определите 1 главный приоритет, чтобы не распыляться.\n"
            f"• Смело выходите на важные диалоги — ваши аргументы будут услышаны.\n"
            f"• Оставьте время для эстетики и отдыха: в спешке Весы теряют чуткость.\n\n"
            f"🗝 <b>Ориентир удачи:</b> число <b>{ctx.lucky_number}</b> • цвет <i>{ctx.lucky_color}</i>\n\n"
            f"{cta}{footer}"
        )

    else:  # forecast
        love_tip = _pick(LOVE_FORECASTS, seed_base + "-love")
        career_tip = _pick(CAREER_FORECASTS, seed_base + "-career")
        title = f"Астропрогноз для Весов на {ctx.date_human}"
        card_headline = f"АСТРОПРОГНОЗ • {ctx.date_human.upper()}"
        card_subline = f"{ctx.libra_aspect}"
        post_html = (
            f"⚖️ <b>АСТРОПРОГНОЗ ДЛЯ ВЕСОВ — {ctx.date_human.upper()}</b>\n"
            f"<i>{ctx.weekday_name} (управитель: {ctx.planet_ruler}) • Луна в {ctx.moon_sign_locative} {ctx.moon_symbol}</i>\n\n"
            f"🌌 <b>Общая атмосфера:</b>\n"
            f"{ctx.libra_aspect} задаёт тон дня — {ctx.libra_aspect_tone}. {element_tip}\n\n"
            f"💼 <b>Дела и финансы ({_stars(ctx.career_score)}):</b>\n{career_tip}\n\n"
            f"❤️ <b>Любовь и общение ({_stars(ctx.love_score)}):</b>\n{love_tip}\n\n"
            f"✨ <b>Подсказки дня:</b>\n"
            f"• Луна: {ctx.moon_phase_name} ({ctx.lunar_day}-й лунный день)\n"
            f"• Цвет: <i>{ctx.lucky_color}</i> • Число: <b>{ctx.lucky_number}</b> • Часы удачи: {ctx.lucky_hours}\n\n"
            f"{cta}{footer}"
        )

    return {
        "title": title,
        "card_headline": card_headline,
        "card_subline": card_subline,
        "post_html": post_html,
        "source": "offline_engine",
    }
