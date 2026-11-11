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


# ── Вариативные вступления и концовки: делают офлайн-тексты менее шаблонными ──
OPENINGS = {
    "forecast": [
        "День складывается в вашу пользу — если не спешить и держать внутреннюю опору.",
        "С утра включите наблюдателя: сегодня детали важнее громких заявлений.",
        "Небо подготовило для Весов мягкую, но значимую развилку.",
        "Есть особая прелесть в этом дне: он просит не скорости, а точности выбора.",
        "Сегодня ваш главный инструмент — вкус: к людям, к словам, к собственному времени.",
    ],
    "tarot": [
        "Карта легла спокойно и уверенно — она про вашу внутреннюю точку силы.",
        "Аркан дня улыбается Весам: то, что казалось сложным, имеет изящное решение.",
        "Этот аркан приходит с мягкой настойчивостью — не игнорируйте его подсказку.",
        "Посмотрите на карту как на зеркало: она показывает не будущее, а ваш ресурс.",
    ],
    "love": [
        "В воздухе сегодня больше тепла, чем слов — и это ваша стихия.",
        "Любовь в этот день простая: меньше догадок, больше честности.",
        "Венера подсказывает: красота рождается в диалоге, а не в догадках.",
        "Для Весов сегодня особенно важно не путать деликатность с молчанием.",
    ],
    "venus": [
        "Венера не требует подвигов — только внимания к себе.",
        "Сегодняшняя гармония набирается мелкими, почти незаметными жестами.",
        "Роскошь этого дня — в тишине, которую вы себе позволите.",
    ],
    "week_ahead": [
        "Неделя открывается с шансом навести порядок в главном.",
        "Семь дней впереди — это не марафон, а настройка ритма.",
        "Начните неделю с одного честного решения — дальше пойдёт легче.",
    ],
}

CLOSINGS = {
    "forecast": [
        "Пусть день пройдёт ровно, как хорошие весы: без перекосов в чужую сторону.",
        "Ваша сила сегодня — в спокойной ясности, а не в доказательствах.",
        "Берегите баланс: он у вас в крови.",
    ],
    "tarot": [
        "Доверяйте первому импульсу — он сегодня точнее долгих раздумий.",
        "Оставьте себе право на паузу: в ней прячется удачный ответ.",
    ],
    "love": [
        "Одно тёплое слово сегодня стоит длинного разговора завтра.",
        "Позвольте себе быть любимыми без условий и экзаменов.",
    ],
    "venus": [
        "Красота — это форма уважения к себе. Выберите её сегодня.",
        "Мягкость — не слабость. Сегодня она ваш главный козырь.",
    ],
    "week_ahead": [
        "Пусть неделя будет про ваш ритм, а не про чужие ожидания.",
        "Один маленький шаг в понедельник — целая победа к пятнице.",
    ],
}


def _pick(items: list[str], seed: str) -> str:
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return items[int.from_bytes(h[:4], "big") % len(items)]


def _stars(score: int) -> str:
    return "★" * score + "☆" * (5 - score)


def _fit_caption(post_html: str, opening: str, closing: str, limit: int = 1000) -> str:
    """Гарантирует, что текст уложится в подпись к фото Telegram (1024 символа).

    Порядок «сжатия»: сначала убираем лирическую концовку, потом вступление,
    и только в крайнем случае аккуратно режем по границе предложения.
    """
    if len(post_html) <= limit:
        return post_html

    for optional in (closing, opening):
        shortened = post_html.replace(f"{optional}\n\n", "", 1)
        if len(shortened) <= limit:
            return shortened
        post_html = shortened

    cut = post_html[: limit - 1]
    for sep in ("\n\n", ". ", "\n"):
        pos = cut.rfind(sep)
        if pos > limit * 0.6:
            cut = cut[:pos] + "…"
            break
    return cut


def generate_fallback_post(ctx: DailyAstroContext, channel_handle: str = "") -> dict[str, Any]:
    """Создаёт готовый структурированный пост и текст карточки без участия LLM."""
    seed_base = f"{ctx.date_iso}-{ctx.slot}-{ctx.rubric_key}"
    phase_tip = PHASE_GUIDANCE.get(ctx.moon_phase_key, "")
    element_tip = ELEMENT_NOTES.get(ctx.moon_element, "")
    cta = _pick(ENGAGEMENT_CTAS, seed_base + "-cta")
    opening = _pick(OPENINGS.get(ctx.rubric_key, OPENINGS["forecast"]), seed_base + "-open")
    closing = _pick(CLOSINGS.get(ctx.rubric_key, CLOSINGS["forecast"]), seed_base + "-close")
    footer = f"\n\n{ctx.rubric_hashtag}" + (f" • {channel_handle}" if channel_handle else "")

    if ctx.rubric_key == "tarot":
        card = ctx.tarot_card
        title = f"Карта дня: {card['numeral']} • {card['name']}"
        card_headline = f"{card['numeral']} • {card['name'].upper()}"
        card_subline = card["keywords"]
        post_html = (
            f"🃏 <b>КАРТА ДНЯ ДЛЯ ВЕСОВ — {ctx.date_human.upper()}</b>\n"
            f"<i>{ctx.weekday_name} • Луна в {ctx.moon_sign_locative} ({ctx.moon_phase_name})</i>\n\n"
            f"{opening}\n\n"
            f"✨ Аркан дня: <b>{card['numeral']}. {card['name']}</b>\n"
            f"<blockquote>{card['keywords']}</blockquote>\n\n"
            f"⚖️ <b>Что это значит для Весов:</b>\n{card['libra_meaning']}\n\n"
            f"🗝 <b>Совет карты:</b> {card['advice']}\n\n"
            f"🔮 <b>Фокус дня:</b> цвет — <i>{ctx.lucky_color}</i>, камень — <i>{ctx.lucky_stone}</i>.\n\n"
            f"{closing}\n\n"
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
            f"{opening}\n\n"
            f"💞 <b>Динамика пары:</b>\n{partner['dynamic']}\n\n"
            f"🌙 <b>Настроение Венеры:</b>\n{love_tip} {element_tip}\n\n"
            f"⚖️ <b>Индекс притяжения:</b> {_stars(ctx.love_score)}\n"
            f"⏰ <b>Удачные часы для свидания и разговоров:</b> {ctx.lucky_hours}\n\n"
            f"{closing}\n\n"
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
            f"{opening}\n\n"
            f"🕊 <b>Настрой дня:</b>\n{phase_tip}\n\n"
            f"✨ <b>Практика для внутреннего баланса:</b>\n{ritual}\n\n"
            f"<blockquote>«Моя красота и сила рождаются там, где я выбираю спокойную ясность вместо сомнений.»</blockquote>\n\n"
            f"{closing}\n\n"
            f"{cta}{footer}"
        )

    elif ctx.rubric_key == "week_ahead":
        title = "Фокус Весов на новую неделю"
        card_headline = "НАСТРОЙКА НА НЕДЕЛЮ"
        card_subline = f"{ctx.moon_phase_name} • Луна в {ctx.moon_sign_locative}"
        post_html = (
            f"🔮 <b>ФОКУС ВЕСОВ НА НОВУЮ НЕДЕЛЮ</b>\n"
            f"<i>{ctx.date_human} • {ctx.moon_phase_name} ({ctx.moon_illumination}%)</i>\n\n"
            f"{opening}\n\n"
            f"⚖️ <b>Главный вектор:</b>\n{ctx.libra_aspect} открывает неделю с акцентом на {ctx.libra_aspect_tone}.\n\n"
            f"🌿 <b>Что важно сделать:</b>\n"
            f"• Определите 1 главный приоритет, чтобы не распыляться.\n"
            f"• Смело выходите на важные диалоги — ваши аргументы будут услышаны.\n"
            f"• Оставьте время для эстетики и отдыха: в спешке Весы теряют чуткость.\n\n"
            f"🗝 <b>Ориентир удачи:</b> число <b>{ctx.lucky_number}</b> • цвет <i>{ctx.lucky_color}</i>\n\n"
            f"{closing}\n\n"
            f"{cta}{footer}"
        )

    elif ctx.rubric_key == "sex":
        title, card_headline, card_subline, post_html = _build_sex_post(
            ctx, seed_base, opening, closing, cta, footer
        )
        post_html = _fit_caption(post_html, opening, closing)

    elif ctx.rubric_key == "love_daily":
        title, card_headline, card_subline, post_html = _build_love_daily(
            ctx, seed_base, opening, closing, cta, footer
        )
        post_html = _fit_caption(post_html, opening, closing)

    elif ctx.rubric_key == "business":
        title, card_headline, card_subline, post_html = _build_business(
            ctx, seed_base, opening, closing, cta, footer
        )
        post_html = _fit_caption(post_html, opening, closing)

    elif ctx.rubric_key == "quiz":
        title, card_headline, card_subline, post_html = _build_quiz(ctx, seed_base, cta, footer)

    elif ctx.rubric_key == "moon_today":
        title, card_headline, card_subline, post_html = _build_moon_today(ctx, footer)

    elif ctx.rubric_key == "month_love":
        title, card_headline, card_subline, post_html = _build_month_post(
            ctx, "love", opening, closing, cta, footer
        )
        post_html = _fit_caption(post_html, opening, closing)

    elif ctx.rubric_key == "month_sex":
        title, card_headline, card_subline, post_html = _build_month_post(
            ctx, "sex", opening, closing, cta, footer
        )
        post_html = _fit_caption(post_html, opening, closing)

    elif ctx.rubric_key == "month_business":
        title, card_headline, card_subline, post_html = _build_month_post(
            ctx, "business", opening, closing, cta, footer
        )
        post_html = _fit_caption(post_html, opening, closing)

    else:  # forecast
        love_tip = _pick(LOVE_FORECASTS, seed_base + "-love")
        career_tip = _pick(CAREER_FORECASTS, seed_base + "-career")
        title = f"Астропрогноз для Весов на {ctx.date_human}"
        card_headline = f"АСТРОПРОГНОЗ • {ctx.date_human.upper()}"
        card_subline = f"{ctx.libra_aspect}"
        post_html = (
            f"⚖️ <b>АСТРОПРОГНОЗ ДЛЯ ВЕСОВ — {ctx.date_human.upper()}</b>\n"
            f"<i>{ctx.weekday_name} (управитель: {ctx.planet_ruler}) • Луна в {ctx.moon_sign_locative} {ctx.moon_symbol}</i>\n\n"
            f"{opening}\n\n"
            f"🌌 <b>Общая атмосфера:</b>\n"
            f"{ctx.libra_aspect} задаёт тон дня — {ctx.libra_aspect_tone}. {element_tip}\n\n"
            f"💼 <b>Дела и финансы ({_stars(ctx.career_score)}):</b>\n{career_tip}\n\n"
            f"❤️ <b>Любовь и общение ({_stars(ctx.love_score)}):</b>\n{love_tip}\n\n"
            f"✨ <b>Подсказки дня:</b>\n"
            f"• Луна: {ctx.moon_phase_name} ({ctx.lunar_day}-й лунный день)\n"
            f"• Цвет: <i>{ctx.lucky_color}</i> • Число: <b>{ctx.lucky_number}</b> • Часы удачи: {ctx.lucky_hours}\n\n"
            f"{closing}\n\n"
            f"{cta}{footer}"
        )

    post_html = _fit_caption(post_html, opening, closing)

    return {
        "title": title,
        "card_headline": card_headline,
        "card_subline": card_subline,
        "post_html": post_html,
        "source": "offline_engine",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  НОВЫЕ РУБРИКИ: секс, любовь с Весами, бизнес, тест, луна, месячные
# ═══════════════════════════════════════════════════════════════════════════

from src.content_extras import (  # noqa: E402
    BIZ_CLIENTS,
    BIZ_FOCUS,
    LIBRA_TYPES,
    LOVE_MODES,
    MONTH_BEST_DAYS,
    MONTH_BIZ,
    MONTH_LOVE,
    MONTH_SEX,
    MONTH_THEMES,
    MONEY_ACTIONS,
    MOON_ONE_LINERS,
    PARTNER_NEEDS,
    SEX_ENERGY_LEVELS,
    SEX_MOODS,
    SEX_TIPS,
    TEST_QUESTIONS,
)


def _sex_energy(score: int) -> tuple[int, str, str]:
    for level, label, note in SEX_ENERGY_LEVELS:
        if score >= level:
            return level, label, note
    return 3, "Умеренная", SEX_ENERGY_LEVELS[-1][2]


def _build_sex_post(ctx, seed_base: str, opening: str, closing: str, cta: str, footer: str):
    partner = ctx.compat_partner
    mood = SEX_MOODS.get(partner["sign"], SEX_MOODS["Весы"])
    tip = _pick(SEX_TIPS, seed_base + "-sex-tip")
    score = min(5, max(3, ctx.energy_score))
    _, level_label, level_note = _sex_energy(score)

    title = f"Секс и чувственность: Весы × {partner['sign']}"
    card_headline = "ЧУВСТВЕННОСТЬ ВЕСОВ"
    card_subline = f"{partner['sign']} • {level_label} энергии"
    post_html = (
        f"🔥 <b>СЕКС И ЧУВСТВЕННОСТЬ — {ctx.date_human.upper()}</b>\n"
        f"<i>Весы ♎ × {partner['sign']} {partner['symbol']} • Луна в {ctx.moon_sign_locative}</i>\n\n"
        f"{opening}\n\n"
        f"💫 <b>Настрой дня — {mood['tone']}:</b>\n{mood['text']}\n\n"
        f"🔥 <b>Уровень желания:</b> {_stars(score)} — {level_label.lower()}\n{level_note}\n\n"
        f"🕯 <b>Практика на вечер:</b>\n{tip}\n\n"
        f"{closing}\n\n"
        f"{cta}{footer}"
    )
    return title, card_headline.replace("ЧУВСТВЕННОСТЬ ВЕСОВ", "ЧУВСТВЕННОСТЬ ВЕСОВ"), card_subline, post_html


def _build_love_daily(ctx, seed_base: str, opening: str, closing: str, cta: str, footer: str):
    partner = ctx.compat_partner
    mode_idx = int.from_bytes(hashlib.sha256((seed_base + "-lovemode").encode()).digest()[:4], "big") % len(LOVE_MODES)
    mode_name, mode_text = LOVE_MODES[mode_idx]
    needs = PARTNER_NEEDS.get(partner["sign"], "нужна искренность и внимание")
    love_tip = _pick(LOVE_FORECASTS, seed_base + "-love")

    title = f"Любовь с Весами: {partner['sign']}"
    card_headline = f"ВЕСЫ × {partner['sign'].upper()}"
    card_subline = f"Любовь • {mode_name}"
    post_html = (
        f"💞 <b>ЛЮБОВЬ С ВЕСАМИ — {ctx.date_human.upper()}</b>\n"
        f"<i>Весы ♎ × {partner['sign']} {partner['symbol']} • {ctx.weekday_name}</i>\n\n"
        f"{opening}\n\n"
        f"💗 <b>Как сегодня проявляется любовь:</b>\n{mode_text}\n\n"
        f"🤝 <b>Что нужно вашему человеку:</b>\n{partner['sign']} — {needs}.\n\n"
        f"⚖️ <b>Баланс пары:</b>\n{love_tip}\n\n"
        f"⏰ <b>Часы для разговоров и свиданий:</b> {ctx.lucky_hours}\n\n"
        f"{closing}\n\n"
        f"{cta}{footer}"
    )
    return title, card_headline, card_subline, post_html


def _build_business(ctx, seed_base: str, opening: str, closing: str, cta: str, footer: str):
    partner = ctx.compat_partner
    focus_name, focus_text = BIZ_FOCUS[
        int.from_bytes(hashlib.sha256((seed_base + "-biz").encode()).digest()[:4], "big") % len(BIZ_FOCUS)
    ]
    money = _pick(MONEY_ACTIONS, seed_base + "-money")
    client_note = BIZ_CLIENTS.get(partner["sign"], "ценит ясность и уважение")

    title = f"Бизнес с Весами: {focus_name}"
    card_headline = "БИЗНЕС ВЕСОВ"
    card_subline = f"{focus_name} • дела {ctx.career_score}/5"
    post_html = (
        f"💼 <b>БИЗНЕС И ДЕНЬГИ — {ctx.date_human.upper()}</b>\n"
        f"<i>Управитель дня: {ctx.planet_ruler} • Луна в {ctx.moon_sign_locative}</i>\n\n"
        f"{opening}\n\n"
        f"🎯 <b>Фокус дня — {focus_name.lower()}:</b>\n{focus_text}\n\n"
        f"🤝 <b>Партнёры и клиенты:</b>\nСегодня сильнее всего откликаются {partner['sign']} {partner['symbol']} — {client_note}.\n\n"
        f"💰 <b>Деньги:</b>\n{money}\n\n"
        f"📈 <b>Индекс дел:</b> {_stars(ctx.career_score)}\n"
        f"⏰ <b>Часы для переговоров:</b> {ctx.lucky_hours}\n\n"
        f"{closing}\n\n"
        f"{cta}{footer}"
    )
    return title, card_headline, card_subline, post_html


def _build_quiz(ctx, seed_base: str, cta: str, footer: str):
    ltype = ctx.libra_type or LIBRA_TYPES[0]
    others = [t for t in LIBRA_TYPES if t["id"] != ltype["id"]]

    title = f"Тест: какой вы Весы? ({ltype['name']})"
    card_headline = "КАКОЙ ВЫ ВЕСЫ?"
    card_subline = ltype["name"]
    options = "\n".join(
        f"{i}. <b>{t['name']}</b> — {t['lead'].lower()}" for i, t in enumerate(LIBRA_TYPES, 1)
    )
    post_html = (
        f"🎭 <b>ТЕСТ: КАКОЙ ВЫ ВЕСЫ?</b>\n"
        f"<i>{ctx.date_human} • {ctx.moon_phase_name}</i>\n\n"
        f"Все знают, что Весы — про баланс. Но баланс у всех разный.\nВыберите, что вам ближе сегодня:\n\n"
        f"{options}\n\n"
        f"<blockquote>Напишите цифру в комментариях — расскажу, что это значит именно для вас.</blockquote>\n\n"
        f"✨ <b>Тип дня:</b> {ltype['name']} — {ltype['desc']}\n\n"
        f"🗝 <b>Сильная сторона:</b> {ltype['strength']}.\n"
        f"⚠️ <b>Риск:</b> {ltype['risk']}.\n"
        f"💡 <b>Совет:</b> {ltype['advice']}\n\n"
        f"{cta}{footer}"
    )
    return title, card_headline, card_subline, post_html


def _build_moon_today(ctx, footer: str):
    one_liner = MOON_ONE_LINERS.get(ctx.moon_phase_key, "День просит внимания к себе.")
    title = f"Луна сегодня: {ctx.moon_phase_name}"
    card_headline = f"ЛУНА В {ctx.moon_sign.upper()}"
    card_subline = f"{ctx.moon_phase_name} • {ctx.moon_illumination:.0f}%"
    post_html = (
        f"🌙 <b>ЛУНА СЕГОДНЯ</b>\n"
        f"<i>{ctx.date_human} • {ctx.lunar_day}-й лунный день</i>\n\n"
        f"<b>{ctx.moon_phase_name}</b> • освещённость {ctx.moon_illumination:.0f}%\n"
        f"Луна в {ctx.moon_sign_locative} {ctx.moon_symbol} — стихия {ctx.moon_element}\n\n"
        f"<blockquote>{one_liner}</blockquote>\n\n"
        f"⚖️ Для Весов: {ctx.libra_aspect_tone}.\n\n"
        f"🔁 Перешлите тому, кому это сейчас нужно.{footer}"
    )
    return title, card_headline, card_subline, post_html


MONTH_OPENINGS = {
    "love": "Месяц, в котором сердце наконец перестаёт сомневаться.",
    "sex": "Месяц, когда чувственность становится способом говорить правду.",
    "business": "Месяц, в котором выигрывает не самый быстрый, а самый точный.",
}

MONTH_CLOSINGS = {
    "love": "Пусть этот месяц будет про выбор, а не про ожидание.",
    "sex": "Разрешите себе хотеть — это и есть ваша сила.",
    "business": "Один верный договор в этом месяце стоит десяти попыток.",
}


def _build_month_post(ctx, slot_type: str, opening: str, closing: str, cta: str, footer: str):
    """Месячные прогнозы: любовь / секс / бизнес на следующий месяц."""
    opening = MONTH_OPENINGS.get(slot_type, opening)
    closing = MONTH_CLOSINGS.get(slot_type, closing)
    month = ctx.target_month_name
    best = MONTH_BEST_DAYS[ctx.target_month % len(MONTH_BEST_DAYS)]
    theme = MONTH_THEMES[ctx.target_month % len(MONTH_THEMES)]

    if slot_type == "love":
        text = MONTH_LOVE["Весы"]
        title = f"Любовь Весов на {month}"
        card_headline = f"ЛЮБОВЬ • {ctx.target_month_name.upper()}"
        card_subline = "Прогноз на месяц"
        body = (
            f"💞 <b>ЛЮБОВЬ ВЕСОВ НА {month.upper()}</b>\n"
            f"<i>Прогноз на месяц • {theme}</i>\n\n"
            f"{opening}\n\n"
            f"💗 <b>Главное:</b>\n{text}\n\n"
            f"🌙 <b>Тон месяца:</b> {ctx.libra_aspect} — {ctx.libra_aspect_tone}.\n\n"
            f"🗓 <b>Удачные дни для признаний и встреч:</b> {best}\n\n"
            f"{closing}\n\n"
            f"{cta}{footer}"
        )
    elif slot_type == "sex":
        text = MONTH_SEX["Весы"]
        title = f"Чувственность Весов на {month}"
        card_headline = f"СТРАСТЬ • {ctx.target_month_name.upper()}"
        card_subline = "Прогноз на месяц"
        body = (
            f"🔥 <b>ЧУВСТВЕННОСТЬ ВЕСОВ НА {month.upper()}</b>\n"
            f"<i>Прогноз на месяц • {theme}</i>\n\n"
            f"{opening}\n\n"
            f"💫 <b>Главное:</b>\n{text}\n\n"
            f"🕯 <b>Практика месяца:</b>\nПопробуйте один раз то, что давно откладывали: разговор, место, признание. Именно неожиданность в этом месяце работает сильнее привычного сценария.\n\n"
            f"🗓 <b>Лучшие дни:</b> {best}\n\n"
            f"{closing}\n\n"
            f"{cta}{footer}"
        )
    else:
        text = MONTH_BIZ["Весы"]
        title = f"Бизнес Весов на {month}"
        card_headline = f"БИЗНЕС • {ctx.target_month_name.upper()}"
        card_subline = "Прогноз на месяц"
        body = (
            f"💼 <b>БИЗНЕС ВЕСОВ НА {month.upper()}</b>\n"
            f"<i>Прогноз на месяц • {theme}</i>\n\n"
            f"{opening}\n\n"
            f"🎯 <b>Главное:</b>\n{text}\n\n"
            f"💰 <b>Деньги:</b>\nВ этом месяце выигрывают партнёрства и договорённости — один человек может открыть больше дверей, чем десять попыток в одиночку.\n\n"
            f"🗓 <b>Удачные дни для сделок и переговоров:</b> {best}\n\n"
            f"{closing}\n\n"
            f"{cta}{footer}"
        )
    return title, card_headline, card_subline, body
