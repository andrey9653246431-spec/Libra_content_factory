"""Бесплатный генератор брендированных Таро-карточек (PNG) в стиле аватарки канала."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from src.astro_engine import DailyAstroContext

# Палитра, согласованная с assets/libra_avatar.png
BG_DARK = (11, 16, 24)
BG_CENTER = (22, 30, 44)
GOLD_BRIGHT = (244, 229, 192)
GOLD_MAIN = (226, 200, 138)
GOLD_MUTED = (160, 136, 86)
GOLD_DIM = (82, 70, 46)
MOON_DARK = (18, 25, 37)

FONT_SERIF_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
]
FONT_SERIF_REG_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
]
FONT_SANS_REG_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(candidates: Iterable[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _clean_serif_text(text: str) -> str:
    """Оставляет только символы, гарантированно поддерживаемые классическим Serif-шрифтом."""
    replacements = {
        "♕": "Q",
        "♔": "K",
        "♗": "P",
        "♘": "Kn",
        "♎": "",
        "♈": "",
        "♉": "",
        "♊": "",
        "♋": "",
        "♌": "",
        "♍": "",
        "♏": "",
        "♐": "",
        "♑": "",
        "♒": "",
        "♓": "",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Убираем прочие эмодзи/неподдерживаемые символы за пределами кириллицы/латиницы/пунктуации
    text = re.sub(r"[^\w\s@\.,:;!\?\-\—\–•×◆«»\"'()°/%№]", "", text, flags=re.UNICODE)
    return re.sub(r"\s{2,}", " ", text).strip()


def _sentence_case(text: str) -> str:
    """«Лев • Максимум энергия» → «Лев • максимум энергия» (аккуратный подзаголовок)."""
    if not text:
        return text
    out = []
    start_of_phrase = True
    for ch in text:
        if ch.isalpha() and start_of_phrase and ch.isupper():
            out.append(ch.lower() if out and out[-1] not in "•—-" else ch)
        else:
            out.append(ch)
        start_of_phrase = ch in "  " or ch in "•—–-"
    return "".join(out)


def _draw_4point_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r_outer: float, r_inner: float, fill: tuple[int, int, int]) -> None:
    pts = []
    for i in range(8):
        angle = math.radians(i * 45 - 90)
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=fill)


def _draw_8point_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r_outer: float, fill: tuple[int, int, int]) -> None:
    for i in range(24):
        angle = math.radians(i * 15)
        length = r_outer if i % 6 == 0 else (r_outer * 0.62 if i % 3 == 0 else r_outer * 0.38)
        w = 4 if i % 6 == 0 else 2
        x1 = cx + length * math.cos(angle)
        y1 = cy + length * math.sin(angle)
        x2 = cx - length * math.cos(angle)
        y2 = cy - length * math.sin(angle)
        draw.line([(x1, y1), (x2, y2)], fill=fill, width=w)
    _draw_4point_star(draw, cx, cy, r_outer * 0.42, r_outer * 0.14, GOLD_BRIGHT)
    draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=BG_DARK, outline=GOLD_BRIGHT, width=3)


def _draw_5point_star(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r_outer: float,
    filled: bool,
    color: tuple[int, int, int],
) -> None:
    pts = []
    r_inner = r_outer * 0.42
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    if filled:
        draw.polygon(pts, fill=color)
    else:
        draw.polygon(pts, outline=color, width=3)


def _draw_diamond(draw: ImageDraw.ImageDraw, cx: float, cy: float, rx: float, ry: float, fill: tuple[int, int, int]) -> None:
    draw.polygon([(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)], fill=fill)


def _draw_moon_phase(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ctx: DailyAstroContext) -> None:
    """Рисует точную сегодняшнюю фазу Луны внутри астролябии."""
    # Основа диска (теневая сторона)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=MOON_DARK, outline=GOLD_MAIN, width=3)

    # Угол элонгации вычисляется приближённо из освещённости и стороны роста
    illum = max(0.0, min(1.0, ctx.moon_illumination / 100.0))
    waxing = ctx.moon_age_days <= 14.765

    # Попиксельная отрисовка терминатора для гладкой реалистичной фазы
    k = 1.0 - 2.0 * illum  # +1 = новолуние, 0 = четверть, -1 = полнолуние
    steps = int(r)
    for dy in range(-steps, steps + 1):
        y_norm = dy / r
        half_w = math.sqrt(max(0.0, 1.0 - y_norm * y_norm))
        x_edge = half_w * r
        x_term = half_w * k * r
        if waxing:
            # Освещена правая часть: от x_term до +x_edge
            x_left = cx + x_term
            x_right = cx + x_edge
        else:
            # Освещена левая часть: от -x_edge до -x_term
            x_left = cx - x_edge
            x_right = cx - x_term
        if x_right > x_left + 0.5:
            draw.line([(x_left, cy + dy), (x_right, cy + dy)], fill=GOLD_BRIGHT, width=2)

    # Лёгкие кратеры-штрихи в духе гравюры на светлом ободке
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GOLD_MAIN, width=4)


def _draw_libra_scales(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float = 1.0) -> None:
    """Рисует детализированные винтажные золотые весы (в стиле libra_avatar.png)."""
    s = scale
    # Центральный стержень
    top_y = cy - 155 * s
    bot_y = cy + 165 * s
    draw.line([(cx, top_y), (cx, bot_y)], fill=GOLD_MAIN, width=max(3, int(8 * s)))
    # Верхнее навершие
    _draw_diamond(draw, cx, top_y - 12 * s, 14 * s, 22 * s, GOLD_BRIGHT)
    draw.ellipse((cx - 18 * s, top_y + 18 * s, cx + 18 * s, top_y + 54 * s), outline=GOLD_BRIGHT, width=max(2, int(4 * s)))
    # Нижний наконечник
    _draw_diamond(draw, cx, bot_y + 14 * s, 14 * s, 24 * s, GOLD_BRIGHT)
    # Поперечные кольца на стержне
    for ky in (-40, 10, 65):
        draw.line([(cx - 16 * s, cy + ky * s), (cx + 16 * s, cy + ky * s)], fill=GOLD_BRIGHT, width=max(2, int(5 * s)))

    # Изогнутое коромысло весов
    beam_y = cy - 92 * s
    span = 225 * s
    pts_left = []
    pts_right = []
    for i in range(25):
        t = i / 24.0
        x = t * span
        # Волнообразный изгиб коромысла
        y_off = -18 * s * math.sin(t * math.pi) + 10 * s * math.sin(t * 2 * math.pi)
        pts_left.append((cx - x, beam_y + y_off))
        pts_right.append((cx + x, beam_y + y_off))
    draw.line(pts_left, fill=GOLD_MAIN, width=max(3, int(7 * s)))
    draw.line(pts_right, fill=GOLD_MAIN, width=max(3, int(7 * s)))

    # Левая и правая чаши на цепях
    for side in (-1, 1):
        hook_x = cx + side * span
        hook_y = beam_y
        draw.ellipse((hook_x - 8 * s, hook_y - 8 * s, hook_x + 8 * s, hook_y + 8 * s), fill=GOLD_BRIGHT)

        pan_y = cy + 108 * s
        pan_w = 108 * s
        left_x = hook_x - pan_w
        right_x = hook_x + pan_w

        # Три подвесные цепи (с лёгкой имитацией звеньев)
        for tx in (left_x + 8 * s, hook_x, right_x - 8 * s):
            draw.line([(hook_x, hook_y), (tx, pan_y)], fill=GOLD_MUTED, width=max(2, int(3 * s)))
            for step in range(2, 9):
                lx = hook_x + (tx - hook_x) * (step / 9.0)
                ly = hook_y + (pan_y - hook_y) * (step / 9.0)
                draw.ellipse((lx - 4 * s, ly - 4 * s, lx + 4 * s, ly + 4 * s), fill=GOLD_MAIN)

        # Чаша (полумесяц / блюдце)
        draw.arc(
            (left_x, pan_y - 36 * s, right_x, pan_y + 42 * s),
            start=0,
            end=180,
            fill=GOLD_BRIGHT,
            width=max(3, int(6 * s)),
        )
        draw.arc(
            (left_x, pan_y - 16 * s, right_x, pan_y + 38 * s),
            start=0,
            end=180,
            fill=GOLD_BRIGHT,
            width=max(2, int(4 * s)),
        )
        draw.line([(left_x - 6 * s, pan_y + 10 * s), (right_x + 6 * s, pan_y + 10 * s)], fill=GOLD_BRIGHT, width=max(2, int(4 * s)))


def _draw_tarot_cartouche(draw: ImageDraw.ImageDraw, cx: float, cy: float, numeral: str, font_num: ImageFont.ImageFont) -> None:
    """Рисует золотую карту Таро с римским номером внутри астролябии."""
    w, h = 230, 340
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    draw.rounded_rectangle((x0, y0, x1, y1), radius=24, fill=(15, 22, 34), outline=GOLD_MAIN, width=5)
    draw.rounded_rectangle((x0 + 14, y0 + 14, x1 - 14, y1 - 14), radius=16, outline=GOLD_MUTED, width=2)
    # Лучи вокруг карты
    for i in range(16):
        ang = math.radians(i * 22.5)
        r1 = 210
        r2 = 250 if i % 2 == 0 else 230
        draw.line(
            [(cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)), (cx + r2 * math.cos(ang), cy + r2 * math.sin(ang))],
            fill=GOLD_DIM,
            width=2,
        )
    # Символ весов-мини и римская цифра
    _draw_4point_star(draw, cx, y0 + 54, 18, 6, GOLD_BRIGHT)
    clean_num = _clean_serif_text(numeral) or "XI"
    bbox = draw.textbbox((0, 0), clean_num, font=font_num)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1] - 10), clean_num, font=font_num, fill=GOLD_BRIGHT)
    _draw_diamond(draw, cx, y1 - 54, 12, 18, GOLD_MAIN)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
    # Добавляем остаток слов в последнюю строку
    used_count = sum(len(l.split()) for l in lines)
    rest = " ".join(words[used_count:])
    if rest:
        # Укорачиваем при необходимости
        while True:
            bbox = draw.textbbox((0, 0), rest, font=font)
            if bbox[2] - bbox[0] <= max_width or len(rest) <= 8:
                break
            rest = rest.rsplit(" ", 1)[0] + "…"
        lines.append(rest)
    return lines[:max_lines]


def render_daily_card(
    ctx: DailyAstroContext,
    headline: str,
    subline: str,
    output_path: Path,
    channel_handle: str = "",
) -> Path:
    """Рендерит 1080x1350 PNG-карточку (с 2x суперсэмплингом для идеальной чёткости).

    Для рубрики «Луна сегодня» автоматически используется короткий макет:
    только фаза, знак и одна строка — именно такой пост чаще всего пересылают.
    """
    if ctx.rubric_key == "moon_today":
        return render_moon_card(ctx, headline, subline, output_path, channel_handle)

    W, H = 2160, 2700  # 2x для антиалиасинга, затем уменьшим до 1080x1350
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Мягкий радиальный градиент в центре
    cx, cy_med = W // 2, 1080
    for r in range(1100, 50, -30):
        t = 1.0 - (r / 1100.0)
        col = tuple(int(BG_DARK[i] + (BG_CENTER[i] - BG_DARK[i]) * (t ** 1.6)) for i in range(3))
        draw.ellipse((cx - r, cy_med - r, cx + r, cy_med + r), fill=col)

    # Россыпь звёзд по фону (детерминирована по дате)
    seed_bytes = hashlib.sha256(f"stars-{ctx.date_iso}-{ctx.rubric_key}".encode("utf-8")).digest()
    for i in range(95):
        h = hashlib.sha256(seed_bytes + bytes([i])).digest()
        sx = 120 + (int.from_bytes(h[0:2], "big") % (W - 240))
        sy = 120 + (int.from_bytes(h[2:4], "big") % (H - 240))
        # Не засоряем зону текста внизу и по краям заголовка
        if (1560 < sy < 2600) or (sy < 320 and 450 < sx < 1710):
            continue
        if h[4] % 9 == 0:
            _draw_4point_star(draw, sx, sy, 14, 4, GOLD_MUTED)
        else:
            rad = 2 + (h[5] % 4)
            col = GOLD_MAIN if h[6] % 3 == 0 else GOLD_DIM
            draw.ellipse((sx - rad, sy - rad, sx + rad, sy + rad), fill=col)

    # Двойная винтажная рамка Таро
    draw.rectangle((66, 66, W - 66, H - 66), outline=GOLD_MAIN, width=4)
    draw.rectangle((92, 92, W - 92, H - 92), outline=GOLD_DIM, width=2)
    for px, py in ((92, 92), (W - 92, 92), (92, H - 92), (W - 92, H - 92)):
        draw.ellipse((px - 22, py - 22, px + 22, py + 22), fill=BG_DARK, outline=GOLD_MAIN, width=3)
        _draw_4point_star(draw, px, py, 16, 5, GOLD_BRIGHT)

    # Шрифты
    font_badge = _load_font(FONT_SERIF_BOLD_CANDIDATES, 40)
    font_date = _load_font(FONT_SERIF_REG_CANDIDATES, 36)
    font_head = _load_font(FONT_SERIF_BOLD_CANDIDATES, 74)
    font_sub = _load_font(FONT_SERIF_REG_CANDIDATES, 44)
    font_meta_lbl = _load_font(FONT_SERIF_REG_CANDIDATES, 28)
    font_meta_val = _load_font(FONT_SERIF_BOLD_CANDIDATES, 34)
    font_num = _load_font(FONT_SERIF_BOLD_CANDIDATES, 118)
    font_footer = _load_font(FONT_SERIF_REG_CANDIDATES, 32)

    # Верхний блок: рубрика + дата
    badge_text = _clean_serif_text(ctx.rubric_badge.upper())
    bb = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw = bb[2] - bb[0]
    draw.text((cx - bw / 2 - bb[0], 145), badge_text, font=font_badge, fill=GOLD_BRIGHT)
    line_gap = 40
    if cx - bw / 2 - line_gap > 200:
        draw.line([(200, 168), (cx - bw / 2 - line_gap, 168)], fill=GOLD_MUTED, width=2)
        draw.line([(cx + bw / 2 + line_gap, 168), (W - 200, 168)], fill=GOLD_MUTED, width=2)
        _draw_diamond(draw, cx - bw / 2 - line_gap, 168, 9, 9, GOLD_MAIN)
        _draw_diamond(draw, cx + bw / 2 + line_gap, 168, 9, 9, GOLD_MAIN)

    date_line = _clean_serif_text(f"{ctx.date_human.upper()}  •  {ctx.weekday_name.upper()}")
    db = draw.textbbox((0, 0), date_line, font=font_date)
    draw.text((cx - (db[2] - db[0]) / 2 - db[0], 218), date_line, font=font_date, fill=GOLD_MUTED)

    # Центральный круг-астролябия
    outer_r = 560
    mid_r = 505
    inner_r = 455
    draw.ellipse((cx - outer_r, cy_med - outer_r, cx + outer_r, cy_med + outer_r), outline=GOLD_MAIN, width=4)
    draw.ellipse((cx - mid_r, cy_med - mid_r, cx + mid_r, cy_med + mid_r), outline=GOLD_MUTED, width=2)
    draw.ellipse((cx - inner_r, cy_med - inner_r, cx + inner_r, cy_med + inner_r), outline=GOLD_MAIN, width=3)

    # Деления шкалы астролябии (360°)
    for deg in range(0, 360, 5):
        ang = math.radians(deg)
        r1 = inner_r + 4
        r2 = mid_r - 4 if deg % 30 == 0 else (inner_r + 28 if deg % 15 == 0 else inner_r + 16)
        w = 3 if deg % 30 == 0 else 2
        col = GOLD_MAIN if deg % 30 == 0 else GOLD_DIM
        draw.line(
            [(cx + r1 * math.cos(ang), cy_med + r1 * math.sin(ang)), (cx + r2 * math.cos(ang), cy_med + r2 * math.sin(ang))],
            fill=col,
            width=w,
        )

    # 4 малые звезды по сторонам астролябии
    for ang_deg in (45, 135, 225, 315):
        ang = math.radians(ang_deg)
        sx = cx + (outer_r + 48) * math.cos(ang)
        sy = cy_med + (outer_r + 48) * math.sin(ang)
        _draw_4point_star(draw, sx, sy, 22, 6, GOLD_MAIN)

    # Полярная звезда на вершине круга
    _draw_8point_star(draw, cx, cy_med - outer_r, 85, GOLD_MAIN)

    # Созвездие Весы фоном внутри круга
    constellation = [
        (cx - 290, cy_med + 40),
        (cx - 210, cy_med - 110),
        (cx + 210, cy_med - 125),
        (cx + 305, cy_med + 30),
    ]
    draw.line(constellation, fill=GOLD_DIM, width=2)
    for px, py in constellation:
        _draw_4point_star(draw, px, py, 14, 4, GOLD_MUTED)

    # Реальная сегодняшняя фаза Луны в верхней части медальона
    moon_y = cy_med - 270
    _draw_moon_phase(draw, cx, moon_y, 92, ctx)

    # Главный символ в центре медальона (зависит от рубрики)
    if ctx.card_theme == "tarot":
        _draw_tarot_cartouche(draw, cx, cy_med + 95, ctx.tarot_card["numeral"], font_num)
    else:
        _draw_libra_scales(draw, cx, cy_med + 100, scale=1.02)

        if ctx.card_theme in ("love", "month_love"):
            # Два переплетённых кольца над весами
            draw.ellipse((cx - 48, cy_med - 160, cx + 10, cy_med - 102), outline=GOLD_BRIGHT, width=3)
            draw.ellipse((cx - 10, cy_med - 160, cx + 48, cy_med - 102), outline=GOLD_MAIN, width=3)

        elif ctx.card_theme in ("sex", "month_sex"):
            # Символ Венеры под стержнем — знак чувственности дня
            _draw_venus_symbol(draw, cx, cy_med + 344, 54)

        elif ctx.card_theme in ("business", "month_business"):
            # Две монеты по бокам под чашами — «деньги и рост»
            _draw_coin(draw, cx - 158, cy_med + 316, 46)
            _draw_coin(draw, cx + 158, cy_med + 316, 46)

        elif ctx.card_theme == "quiz":
            # Две театральные маски по бокам под чашами
            _draw_mask(draw, cx - 158, cy_med + 312, 46, smile=False)
            _draw_mask(draw, cx + 158, cy_med + 312, 46, smile=True)

        elif ctx.card_theme == "moon":
            # Луна уже нарисована выше — добавл	яем тонкий ореол
            draw.arc((cx - 150, cy_med - 420, cx + 150, cy_med - 120), 200, 340, fill=GOLD_DIM, width=2)

    # Заголовок карточки (ниже астролябии)
    clean_head = _clean_serif_text(headline.upper()) or "ВЕСЫ • ПРОГНОЗ"
    head_lines = _wrap_text(draw, clean_head, font_head, max_width=1720, max_lines=2)
    y_cursor = 1755
    for line in head_lines:
        lb = draw.textbbox((0, 0), line, font=font_head)
        lw, lh = lb[2] - lb[0], lb[3] - lb[1]
        draw.text((cx - lw / 2 - lb[0], y_cursor), line, font=font_head, fill=GOLD_BRIGHT)
        y_cursor += lh + 26

    # Декоративный разделитель
    div_y = y_cursor + 24
    draw.line([(420, div_y), (cx - 48, div_y)], fill=GOLD_MUTED, width=2)
    draw.line([(cx + 48, div_y), (W - 420, div_y)], fill=GOLD_MUTED, width=2)
    _draw_diamond(draw, cx, div_y, 16, 16, GOLD_MAIN)

    # Подзаголовок карточки
    clean_sub = _sentence_case(_clean_serif_text(subline))
    sub_lines = _wrap_text(draw, clean_sub, font_sub, max_width=1660, max_lines=2)
    y_sub = div_y + 42
    for line in sub_lines:
        sb = draw.textbbox((0, 0), line, font=font_sub)
        sw, sh = sb[2] - sb[0], sb[3] - sb[1]
        draw.text((cx - sw / 2 - sb[0], y_sub), line, font=font_sub, fill=GOLD_MAIN)
        y_sub += sh + 18

    # Нижняя панель астрономической телеметрии (3 колонки)
    box_top = 2125
    box_bot = 2310
    draw.rounded_rectangle((170, box_top, W - 170, box_bot), radius=24, fill=(14, 20, 31), outline=GOLD_DIM, width=2)
    cols = [
        ("ЛУНА В ЗНАКЕ", ctx.moon_sign.upper()),
        ("ФАЗА ЛУНЫ", ctx.moon_phase_name.upper()),
        ("ЛУННЫЙ ДЕНЬ", f"{ctx.lunar_day}-Й ({ctx.moon_illumination:.0f}%)"),
    ]
    col_w = (W - 340) / 3.0
    for idx, (lbl, val) in enumerate(cols):
        col_cx = 170 + col_w * (idx + 0.5)
        if idx > 0:
            x_sep = 170 + col_w * idx
            draw.line([(x_sep, box_top + 28), (x_sep, box_bot - 28)], fill=GOLD_DIM, width=2)
        lb = draw.textbbox((0, 0), lbl, font=font_meta_lbl)
        draw.text((col_cx - (lb[2] - lb[0]) / 2 - lb[0], box_top + 32), lbl, font=font_meta_lbl, fill=GOLD_MUTED)
        vb = draw.textbbox((0, 0), val, font=font_meta_val)
        draw.text((col_cx - (vb[2] - vb[0]) / 2 - vb[0], box_top + 96), val, font=font_meta_val, fill=GOLD_BRIGHT)

    # Индексы дня со звёздочками (векторными!)
    ratings_y = 2388
    metrics = [
        ("ЛЮБОВЬ", ctx.love_score),
        ("ДЕЛА", ctx.career_score),
        ("ЭНЕРГИЯ", ctx.energy_score),
    ]
    m_col_w = (W - 360) / 3.0
    for idx, (m_lbl, score) in enumerate(metrics):
        mcx = 180 + m_col_w * (idx + 0.5)
        lbl_b = draw.textbbox((0, 0), m_lbl, font=font_meta_lbl)
        draw.text((mcx - (lbl_b[2] - lbl_b[0]) / 2 - lbl_b[0], ratings_y - 42), m_lbl, font=font_meta_lbl, fill=GOLD_MUTED)
        star_gap = 38
        start_x = mcx - 2 * star_gap
        for s_i in range(5):
            _draw_5point_star(
                draw,
                start_x + s_i * star_gap,
                ratings_y + 18,
                14,
                filled=(s_i < score),
                color=GOLD_MAIN if s_i < score else GOLD_DIM,
            )

    # Нижний футер канала
    footer_text = _clean_serif_text(channel_handle if channel_handle else "ВЕСЫ • ЕЖЕДНЕВНЫЙ ПРОГНОЗ")
    fb = draw.textbbox((0, 0), footer_text, font=font_footer)
    draw.text((cx - (fb[2] - fb[0]) / 2 - fb[0], 2518), footer_text, font=font_footer, fill=GOLD_MUTED)

    # Сглаженное уменьшение до 1080x1350
    final_img = img.resize((1080, 1350), Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path, format="PNG", optimize=True)
    return output_path


def _draw_venus_symbol(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    """Символ Венеры ♀ — знак чувственности и притяжения (управитель Весов)."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GOLD_BRIGHT, width=4)
    draw.line([(cx, cy + r), (cx, cy + r * 2.35)], fill=GOLD_BRIGHT, width=4)
    draw.line([(cx - r * 0.72, cy + r * 1.62), (cx + r * 0.72, cy + r * 1.62)], fill=GOLD_MAIN, width=4)
    _draw_diamond(draw, cx, cy + r * 2.55, r * 0.22, r * 0.30, GOLD_MAIN)


def _draw_mask(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, smile: bool) -> None:
    """Театральная маска (для рубрики-теста)."""
    draw.ellipse((cx - r, cy - r * 1.12, cx + r, cy + r * 1.12), outline=GOLD_MAIN, width=3)
    eye_dy = r * 0.30
    for side in (-1, 1):
        ex = cx + side * r * 0.40
        draw.ellipse((ex - r * 0.18, cy - eye_dy - r * 0.13, ex + r * 0.18, cy - eye_dy + r * 0.13), outline=GOLD_BRIGHT, width=2)
    mouth_y = cy + r * 0.34
    box = (cx - r * 0.42, mouth_y - r * 0.26, cx + r * 0.42, mouth_y + r * 0.26)
    if smile:
        draw.arc(box, 20, 160, fill=GOLD_BRIGHT, width=3)
    else:
        draw.arc(box, 200, 340, fill=GOLD_BRIGHT, width=3)


def _draw_coin(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    """Монета с четырёхлучевой звездой — «деньги и рост»."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GOLD_MAIN, width=3)
    draw.ellipse((cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14), outline=GOLD_DIM, width=2)
    _draw_4point_star(draw, cx, cy, r * 1.02, r * 0.36, GOLD_BRIGHT)
    _draw_4point_star(draw, cx, cy, r * 0.52, r * 0.18, GOLD_MAIN)


def _draw_question_cartouche(draw: ImageDraw.ImageDraw, cx: float, cy: float, font_num) -> None:
    """Картуш с «?» — эмблема рубрики-теста."""
    w, h = 132, 168
    draw.rounded_rectangle((cx - w, cy - h, cx + w, cy + h), radius=26, outline=GOLD_MAIN, width=3)
    draw.rounded_rectangle((cx - w + 14, cy - h + 14, cx + w - 14, cy + h - 14), radius=18, outline=GOLD_DIM, width=2)
    q = "?"
    qb = draw.textbbox((0, 0), q, font=font_num)
    draw.text((cx - (qb[2] - qb[0]) / 2 - qb[0], cy - (qb[3] - qb[1]) / 2 - qb[1] - 10), q, font=font_num, fill=GOLD_BRIGHT)
    _draw_diamond(draw, cx, cy - h - 26, 12, 12, GOLD_MAIN)
    _draw_diamond(draw, cx, cy + h + 26, 12, 12, GOLD_MAIN)


def render_moon_card(
    ctx: DailyAstroContext,
    headline: str,
    subline: str,
    output_path: Path,
    channel_handle: str = "",
) -> Path:
    """Короткая карточка «Луна сегодня»: только фаза, знак и одна фраза.

    Без телеметрии и индексов — такой пост идеально пересылают друзьям.
    """
    W, H = 2160, 2700
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, 1180  # центр Луны

    # Мягкий ореол вокруг Луны
    for r in range(820, 120, -22):
        t = 1.0 - (r / 820.0)
        col = tuple(int(BG_DARK[i] + (BG_CENTER[i] - BG_DARK[i]) * (t ** 1.5)) for i in range(3))
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)

    # Звёзды
    seed_bytes = hashlib.sha256(f"moon-{ctx.date_iso}".encode("utf-8")).digest()
    for i in range(120):
        h = hashlib.sha256(seed_bytes + bytes([i])).digest()
        sx = 130 + (int.from_bytes(h[0:2], "big") % (W - 260))
        sy = 130 + (int.from_bytes(h[2:4], "big") % (H - 260))
        dist = ((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5
        if dist < 640:          # не залезаем на Луну
            continue
        if h[4] % 8 == 0:
            _draw_4point_star(draw, sx, sy, 16, 4, GOLD_MUTED)
        else:
            rad = 2 + (h[5] % 4)
            draw.ellipse((sx - rad, sy - rad, sx + rad, sy + rad), fill=GOLD_DIM if h[6] % 3 else GOLD_MAIN)

    # Рамка
    draw.rectangle((66, 66, W - 66, H - 66), outline=GOLD_MAIN, width=4)
    draw.rectangle((92, 92, W - 92, H - 92), outline=GOLD_DIM, width=2)
    for px, py in ((92, 92), (W - 92, 92), (92, H - 92), (W - 92, H - 92)):
        draw.ellipse((px - 22, py - 22, px + 22, py + 22), fill=BG_DARK, outline=GOLD_MAIN, width=3)
        _draw_4point_star(draw, px, py, 16, 5, GOLD_BRIGHT)

    font_badge = _load_font(FONT_SERIF_BOLD_CANDIDATES, 46)
    font_date = _load_font(FONT_SERIF_REG_CANDIDATES, 36)
    font_head = _load_font(FONT_SERIF_BOLD_CANDIDATES, 104)
    font_sub = _load_font(FONT_SERIF_REG_CANDIDATES, 50)
    font_footer = _load_font(FONT_SERIF_REG_CANDIDATES, 32)

    # Бейдж
    badge_text = _clean_serif_text(ctx.rubric_badge.upper() or "ЛУНА СЕГОДНЯ")
    bb = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw = bb[2] - bb[0]
    draw.text((cx - bw / 2 - bb[0], 165), badge_text, font=font_badge, fill=GOLD_BRIGHT)
    line_gap = 44
    if cx - bw / 2 - line_gap > 220:
        draw.line([(220, 190), (cx - bw / 2 - line_gap, 190)], fill=GOLD_MUTED, width=2)
        draw.line([(cx + bw / 2 + line_gap, 190), (W - 220, 190)], fill=GOLD_MUTED, width=2)
        _draw_diamond(draw, cx - bw / 2 - line_gap, 190, 9, 9, GOLD_MAIN)
        _draw_diamond(draw, cx + bw / 2 + line_gap, 190, 9, 9, GOLD_MAIN)

    date_line = _clean_serif_text(f"{ctx.date_human.upper()}  •  {ctx.lunar_day}-Й ЛУННЫЙ ДЕНЬ")
    db = draw.textbbox((0, 0), date_line, font=font_date)
    draw.text((cx - (db[2] - db[0]) / 2 - db[0], 240), date_line, font=font_date, fill=GOLD_MUTED)

    # Тонкое кольцо и сама Луна
    draw.ellipse((cx - 560, cy - 560, cx + 560, cy + 560), outline=GOLD_DIM, width=3)
    _draw_moon_phase(draw, cx, cy, 470, ctx)

    # Название фазы + знак
    y = cy + 700
    phase = _clean_serif_text(ctx.moon_phase_name.upper())
    for line in _wrap_text(draw, phase, font_head, max_width=1700, max_lines=2):
        lb = draw.textbbox((0, 0), line, font=font_head)
        draw.text((cx - (lb[2] - lb[0]) / 2 - lb[0], y), line, font=font_head, fill=GOLD_BRIGHT)
        y += (lb[3] - lb[1]) + 28

    y += 10
    draw.line([(620, y), (cx - 48, y)], fill=GOLD_MUTED, width=2)
    draw.line([(cx + 48, y), (W - 620, y)], fill=GOLD_MUTED, width=2)
    _draw_diamond(draw, cx, y, 16, 16, GOLD_MAIN)

    y += 56
    sub = _sentence_case(_clean_serif_text(subline or f"Луна в {ctx.moon_sign} • {ctx.moon_illumination:.0f}%"))
    for line in _wrap_text(draw, sub, font_sub, max_width=1600, max_lines=2):
        sb = draw.textbbox((0, 0), line, font=font_sub)
        draw.text((cx - (sb[2] - sb[0]) / 2 - sb[0], y), line, font=font_sub, fill=GOLD_MAIN)
        y += (sb[3] - sb[1]) + 20

    # Футер
    footer_text = _clean_serif_text(channel_handle or "ВЕСЫ • ЕЖЕДНЕВНЫЙ ПРОГНОЗ")
    fb = draw.textbbox((0, 0), footer_text, font=font_footer)
    draw.text((cx - (fb[2] - fb[0]) / 2 - fb[0], 2540), footer_text, font=font_footer, fill=GOLD_MUTED)

    final_img = img.resize((1080, 1350), Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path, format="PNG", optimize=True)
    return output_path
