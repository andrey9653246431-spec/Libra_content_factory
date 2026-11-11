"""Астрономический и астрологический движок для знака Весы (без внешних API)."""

from __future__ import annotations

import calendar
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ZODIAC_SIGNS = [
    ("Овен", "Огонь", "♈"),
    ("Телец", "Земля", "♉"),
    ("Близнецы", "Воздух", "♊"),
    ("Рак", "Вода", "♋"),
    ("Лев", "Огонь", "♌"),
    ("Дева", "Земля", "♍"),
    ("Весы", "Воздух", "♎"),
    ("Скорпион", "Вода", "♏"),
    ("Стрелец", "Огонь", "♐"),
    ("Козерог", "Земля", "♑"),
    ("Водолей", "Воздух", "♒"),
    ("Рыбы", "Вода", "♓"),
]

ZODIAC_LOCATIVE = {
    "Овен": "Овне",
    "Телец": "Тельце",
    "Близнецы": "Близнецах",
    "Рак": "Раке",
    "Лев": "Льве",
    "Дева": "Деве",
    "Весы": "Весах",
    "Скорпион": "Скорпионе",
    "Стрелец": "Стрельце",
    "Козерог": "Козероге",
    "Водолей": "Водолее",
    "Рыбы": "Рыбах",
}

MONTHS_GENITIVE = [
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

from src.content_extras import (  # noqa: E402
    LIBRA_TYPES,
    month_genitive_ru,
    month_number_ru,
)

WEEKDAYS_RU = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]

WEEKDAY_RULERS = [
    ("Луна", "интуиция, забота о себе и тонкое настроение"),
    ("Марс", "инициатива, смелые решения и защита границ"),
    ("Меркурий", "переговоры, новости, письма и лёгкость ума"),
    ("Юпитер", "масштаб, удача, щедрость и стратегический взгляд"),
    ("Венера", "ваш главный день-покровитель: любовь, красота, деньги и притяжение"),
    ("Сатурн", "структура, порядок, зрелые выборы и верность себе"),
    ("Солнце", "творческая ясность, уверенность и внутренний свет"),
]

LUCKY_COLORS = [
    "шампань и тёплое золото",
    "глубокий сапфировый",
    "пыльная роза",
    "изумрудный шёлк",
    "кремовый жемчуг",
    "дымчато-лавандовый",
    "бархатный бордо",
    "небесно-голубой",
    "античная бронза",
    "молочный кашемир",
]

STONES_OF_DAY = [
    "розовый кварц",
    "опал",
    "лазурит",
    "цитрин",
    "лунный камень",
    "аквамарин",
    "аметист",
    "сердолик",
    "зелёный авантюрин",
    "горный хрусталь",
]

TAROT_DECK: list[dict[str, str]] = [
    {
        "id": "XI_JUSTICE",
        "numeral": "XI",
        "name": "Справедливость",
        "keywords": "равновесие • ясность • честный выбор",
        "libra_meaning": "Главная карта знака Весы: сегодня правда и внутренний баланс работают на вас. Время взвесить факты без эмоций.",
        "advice": "Принимайте решение там, где долго сомневались, и не занижайте собственную ценность.",
    },
    {
        "id": "VI_LOVERS",
        "numeral": "VI",
        "name": "Влюблённые",
        "keywords": "выбор сердца • притяжение • союз",
        "libra_meaning": "Сильный импульс в теме отношений и личных ценностей. Важно выбрать то, что откликается искренне, а не «из вежливости».",
        "advice": "Скажите тёплое слово тем, кто вам дорог, или откликнитесь на взаимную симпатию.",
    },
    {
        "id": "III_EMPRESS",
        "numeral": "III",
        "name": "Императрица",
        "keywords": "Венера • изобилие • чувственность",
        "libra_meaning": "Карта вашей планеты-управительницы Венеры. День просит красоты вокруг, заботы о теле и созидательного удовольствия.",
        "advice": "Позвольте себе эстетичный жест — вкусный кофе, красивый образ, уют и творческий поток.",
    },
    {
        "id": "XVII_STAR",
        "numeral": "XVII",
        "name": "Звезда",
        "keywords": "вдохновение • надежда • исцеление",
        "libra_meaning": "После сомнений приходит тихая уверенность: вы идёте правильным курсом. Хороший знак для долгих желаний.",
        "advice": "Запишите одну смелую мечту на ближайший месяц и сделайте к ней маленький шаг.",
    },
    {
        "id": "XIV_TEMPERANCE",
        "numeral": "XIV",
        "name": "Умеренность",
        "keywords": "гармония • золотая середина • алхимия",
        "libra_meaning": "Не торопите события. Секрет успеха Весов сегодня — мягко соединить противоположности без крайностей.",
        "advice": "Снизьте темп, если чувствуете суету: нужное письмо или ответ созреют сами.",
    },
    {
        "id": "II_HIGH_PRIESTESS",
        "numeral": "II",
        "name": "Верховная Жрица",
        "keywords": "интуиция • тайные знаки • тишина",
        "libra_meaning": "Логика не даёт полной картины, зато первое тихое ощущение окажется точным. Не раскрывайте планы раньше времени.",
        "advice": "Доверьтесь сну, случайной фразе или внутреннему «да/нет».",
    },
    {
        "id": "X_WHEEL",
        "numeral": "X",
        "name": "Колесо Фортуны",
        "keywords": "поворот судьбы • удачный случай • динамика",
        "libra_meaning": "В воздухе пахнет неожиданным совпадением: звонок, встреча или внезапная смена расписания сыграют вам на руку.",
        "advice": "Будьте гибкими — лучшее предложение дня может прийти не по плану.",
    },
    {
        "id": "XIX_SUN",
        "numeral": "XIX",
        "name": "Солнце",
        "keywords": "радость • признание • открытость",
        "libra_meaning": "Лёгкость, обаяние и видимый результат. Люди охотно тянутся к вашему теплу и чувству вкуса.",
        "advice": "Не прячьте свои успехи — поделитесь идеей или покажите свою работу.",
    },
    {
        "id": "I_MAGICIAN",
        "numeral": "I",
        "name": "Маг",
        "keywords": "мастерство • слово • инициатива",
        "libra_meaning": "У вас уже есть все инструменты, чтобы договориться или запустить задуманное. Ваше слово сегодня особенно убедительно.",
        "advice": "Переходите от обдумывания к первому конкретному действию.",
    },
    {
        "id": "XVIII_MOON",
        "numeral": "XVIII",
        "name": "Луна",
        "keywords": "подсознание • иллюзии • глубина",
        "libra_meaning": "Эмоциональный фон зыбкий — легко додумать то, чего нет. Не верьте тревожным догадкам на слово.",
        "advice": "Перепроверяйте договорённости и берегите вечер для спокойного отдыха.",
    },
    {
        "id": "VIII_STRENGTH",
        "numeral": "VIII",
        "name": "Сила",
        "keywords": "мягкое влияние • достоинство • выдержка",
        "libra_meaning": "Настоящая сила Весов — в спокойной дипломатии и внутренней уверенности, а не в споре на повышенных тонах.",
        "advice": "Укротите сомнения: вы справитесь с задачей мягко и красиво.",
    },
    {
        "id": "XXI_WORLD",
        "numeral": "XXI",
        "name": "Мир",
        "keywords": "завершение этапа • целостность • масштаб",
        "libra_meaning": "Закрывается важный цикл, и вы выходите на новый уровень. Отлично для публикаций, поездок и подведения итогов.",
        "advice": "Поблагодарите себя за пройденный путь и смело открывайте новую дверь.",
    },
    {
        "id": "ACE_CUPS",
        "numeral": "I",
        "name": "Туз Кубков",
        "keywords": "вдохновение • нежность • новый импульс",
        "libra_meaning": "Сердце открывается тёплым эмоциям: возможен приятный жест внимания, комплимент или творческое озарение.",
        "advice": "Примите подарок или доброе отношение без неловкости.",
    },
    {
        "id": "TWO_CUPS",
        "numeral": "II",
        "name": "Двойка Кубков",
        "keywords": "взаимность • примирение • партнёрство",
        "libra_meaning": "Идеальная карта для Весов: диалог на равных, тёплое сближение, удачная деловая или романтическая встреча.",
        "advice": "Идите навстречу — сегодня легко найти общий язык даже в сложном вопросе.",
    },
    {
        "id": "SIX_WANDS",
        "numeral": "VI",
        "name": "Шестёрка Жезлов",
        "keywords": "победа • признание • уверенность",
        "libra_meaning": "Ваши старания заметят и оценят. Хороший день, чтобы заявить о себе или закрыть задачу с блеском.",
        "advice": "Примите похвалу достойно — вы её заслужили.",
    },
    {
        "id": "QUEEN_SWORDS",
        "numeral": "♕",
        "name": "Королева Мечей",
        "keywords": "воздушная стихия • чёткие границы • ум",
        "libra_meaning": "Родная стихия Воздуха даёт трезвый взгляд и элегантную прямоту. Пора отсечь лишнюю суету.",
        "advice": "Скажите вежливое, но твёрдое «нет» тому, что крадёт ваше время.",
    },
    {
        "id": "ACE_PENTACLES",
        "numeral": "I",
        "name": "Туз Пентаклей",
        "keywords": "финансовый шанс • стабильность • подарок",
        "libra_meaning": "Материальный знак удачи: выгодное предложение, премия, полезная покупка или идея для дохода.",
        "advice": "Не упустите практичную возможность — оформите её в конкретный план.",
    },
    {
        "id": "NINE_PENTACLES",
        "numeral": "IX",
        "name": "Девятка Пентаклей",
        "keywords": "самодостаточность • вкус • комфорт",
        "libra_meaning": "Энергия ухоженности, независимости и удовольствия от плодов своего труда. Венера благосклонна к вашим финансам.",
        "advice": "Побалуйте себя качественной вещью или спокойным временем наедине с собой.",
    },
    {
        "id": "KING_CUPS",
        "numeral": "♔",
        "name": "Король Кубков",
        "keywords": "эмоциональная зрелость • такт • поддержка",
        "libra_meaning": "Ваше спокойствие сегодня лечит напряжённую обстановку. Возможен мудрый совет от близкого человека.",
        "advice": "Сохраняйте внутреннее равновесие, даже если вокруг кто-то суетится.",
    },
    {
        "id": "THREE_PENTACLES",
        "numeral": "III",
        "name": "Тройка Пентаклей",
        "keywords": "сотрудничество • мастерство • рост",
        "libra_meaning": "Командная работа и обмен опытом принесут лучший результат, чем попытка тянуть всё в одиночку.",
        "advice": "Обсудите задачу с коллегой или человеком, чьему вкусу вы доверяете.",
    },
    {
        "id": "FOUR_WANDS",
        "numeral": "IV",
        "name": "Четвёрка Жезлов",
        "keywords": "уют • праздник • гармония в доме",
        "libra_meaning": "Атмосфера тепла, гостеприимства и маленького повода для радости. Хорошо для семейных встреч и обустройства пространства.",
        "advice": "Отметьте даже небольшой успех — это закрепит удачную волну.",
    },
    {
        "id": "PAGE_SWORDS",
        "numeral": "♗",
        "name": "Паж Мечей",
        "keywords": "любопытство • свежие идеи • новости",
        "libra_meaning": "Придёт любопытная информация или нестандартный взгляд на старую проблему. Ваш ум сегодня особенно остр.",
        "advice": "Проверьте факты, прежде чем спорить, и запишите внезапный инсайт.",
    },
    {
        "id": "TEN_CUPS",
        "numeral": "X",
        "name": "Десятка Кубков",
        "keywords": "душевная близость • мир • благодарность",
        "libra_meaning": "Редкое ощущение «всё на своих местах». Тёплое общение с близкими снимет накопившееся напряжение.",
        "advice": "Проведите вечер с теми, рядом с кем можно быть собой без масок.",
    },
    {
        "id": "KNIGHT_WANDS",
        "numeral": "♘",
        "name": "Рыцарь Жезлов",
        "keywords": "драйв • смелость • спонтанность",
        "libra_meaning": "День подталкивает выйти из привычной колеи. Хорошо для коротких поездок, флирта и яркой подачи себя.",
        "advice": "Позвольте себе немного азарта там, где обычно слишком долго сомневаетесь.",
    },
]

COMPATIBILITY_PROFILES: list[dict[str, str]] = [
    {"sign": "Овен", "symbol": "♈", "dynamic": "Ось притяжения противоположностей: страсть, искра и вечный поиск баланса между «я» и «мы»."},
    {"sign": "Телец", "symbol": "♉", "dynamic": "Два подопечных Венеры: общая любовь к красоте, комфорту, вкусной жизни и верности."},
    {"sign": "Близнецы", "symbol": "♊", "dynamic": "Лёгкий союз стихии Воздуха: бесконечные разговоры, юмор, общие интересы и свобода."},
    {"sign": "Рак", "symbol": "♋", "dynamic": "Нежность и глубина: Весы приносят лёгкость и такт, а Рак — уют и заботу."},
    {"sign": "Лев", "symbol": "♌", "dynamic": "Яркий, красивый тандем: комплименты, эстетика, вдохновение и взаимное восхищение."},
    {"sign": "Дева", "symbol": "♍", "dynamic": "Союз тонкого вкуса и ясного ума: меньше драмы, больше заботы в мелочах и уважения."},
    {"sign": "Весы", "symbol": "♎", "dynamic": "Зеркальное понимание с полуслова — главное вовремя решать, кто выбирает ресторан."},
    {"sign": "Скорпион", "symbol": "♏", "dynamic": "Магнетизм и тайна: притягивает глубина чувств, важно не уходить в недосказанность."},
    {"sign": "Стрелец", "symbol": "♐", "dynamic": "Союз свободы и приключений: совместные мечты, поездки и рост без скуки."},
    {"sign": "Козерог", "symbol": "♑", "dynamic": "Гармония дипломатии и опоры: Весы смягчают строгость, Козерог даёт надёжность."},
    {"sign": "Водолей", "symbol": "♒", "dynamic": "Воздушное родство душ: свежие идеи, дружба внутри любви и уважение личного пространства."},
    {"sign": "Рыбы", "symbol": "♓", "dynamic": "Романтика, музыка и тонкая эмпатия: союз, где чувства важнее сухих правил."},
]

RUBRICS = {
    "forecast": {
        "key": "forecast",
        "badge": "АСТРОПРОГНОЗ ДНЯ",
        "card_theme": "scales",
        "emoji": "⚖️",
        "hashtag": "#ВесыПрогноз #АстрологияВесы",
    },
    "tarot": {
        "key": "tarot",
        "badge": "КАРТА ДНЯ ТАРО",
        "card_theme": "tarot",
        "emoji": "🃏",
        "hashtag": "#КартаДняВесы #ТароДляВесов",
    },
    "love": {
        "key": "love",
        "badge": "ЛЮБОВЬ И ГАРМОНИЯ",
        "card_theme": "love",
        "emoji": "✨",
        "hashtag": "#ВесыЛюбовь #СовместимостьВесы",
    },
    "venus": {
        "key": "venus",
        "badge": "СОВЕТ ВЕНЕРЫ",
        "card_theme": "moon",
        "emoji": "🌙",
        "hashtag": "#СоветВенеры #ЭнергияВесов",
    },
    "week_ahead": {
        "key": "week_ahead",
        "badge": "ФОКУС НА НЕДЕЛЮ",
        "card_theme": "scales",
        "emoji": "🔮",
        "hashtag": "#ВесыНеделя #ПрогнозВесы",
    },
    # ── Новые ежедневные рубрики ──
    "sex": {
        "key": "sex",
        "badge": "СЕКС И ЧУВСТВЕННОСТЬ",
        "card_theme": "sex",
        "emoji": "🔥",
        "hashtag": "#СексСВесами #ЧувственностьВесов",
    },
    "love_daily": {
        "key": "love_daily",
        "badge": "ЛЮБОВЬ С ВЕСАМИ",
        "card_theme": "love",
        "emoji": "💞",
        "hashtag": "#ЛюбовьСВесами #ОтношенияВесы",
    },
    "business": {
        "key": "business",
        "badge": "БИЗНЕС И ДЕНЬГИ",
        "card_theme": "business",
        "emoji": "💼",
        "hashtag": "#БизнесВесы #ДеньгиВесы",
    },
    "pulse": {
        "key": "pulse",
        "badge": "ВЕСЫ ЗА 15 СЕКУНД",
        "card_theme": "pulse",
        "emoji": "♎",
        "hashtag": "#ВесыЗа15Секунд #ВесыСегодня",
    },
    "quiz": {
        "key": "quiz",
        "badge": "ТЕСТ: КАКОЙ ВЫ ВЕСЫ",
        "card_theme": "quiz",
        "emoji": "🎭",
        "hashtag": "#ТестВесы #КакойТыВесы",
    },
    "moon_today": {
        "key": "moon_today",
        "badge": "ЛУНА СЕГОДНЯ",
        "card_theme": "moon",
        "emoji": "🌙",
        "hashtag": "#ЛунаСегодня #ФазаЛуны",
    },
    # ── Месячные прогнозы (последний день календарного месяца) ──
    "month_love": {
        "key": "month_love",
        "badge": "ЛЮБОВЬ НА МЕСЯЦ",
        "card_theme": "love",
        "emoji": "💞",
        "hashtag": "#ЛюбовьНаМесяц #ПрогнозВесыМесяц",
    },
    "month_sex": {
        "key": "month_sex",
        "badge": "СЕКС НА МЕСЯЦ",
        "card_theme": "sex",
        "emoji": "🔥",
        "hashtag": "#СексНаМесяц #ЧувственностьВесов",
    },
    "month_business": {
        "key": "month_business",
        "badge": "БИЗНЕС НА МЕСЯЦ",
        "card_theme": "business",
        "emoji": "💼",
        "hashtag": "#БизнесНаМесяц #ДеньгиВесов",
    },
}


@dataclass
class DailyAstroContext:
    date_iso: str
    date_human: str
    weekday_name: str
    weekday_index: int
    planet_ruler: str
    planet_theme: str
    sun_sign: str
    sun_degree: float
    moon_sign: str
    moon_sign_locative: str
    moon_symbol: str
    moon_element: str
    moon_degree: float
    moon_phase_key: str
    moon_phase_name: str
    moon_illumination: float
    moon_age_days: float
    lunar_day: int
    libra_aspect: str
    libra_aspect_tone: str
    love_score: int
    career_score: int
    energy_score: int
    lucky_number: int
    lucky_color: str
    lucky_stone: str
    lucky_hours: str
    slot: str
    rubric_key: str
    rubric_badge: str
    card_theme: str
    rubric_emoji: str
    rubric_hashtag: str
    tarot_card: dict[str, str]
    compat_partner: dict[str, str]
    # новые поля
    day_of_month: int = 1
    month_last_day: int = 31
    is_month_end: bool = False
    target_month: int = 1
    target_month_name: str = ""
    target_month_genitive: str = ""
    libra_type: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _julian_day(dt_utc: datetime) -> float:
    y = dt_utc.year
    m = dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + (a // 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _moon_phase_info(elongation_deg: float) -> tuple[str, str]:
    """Возвращает (ключ фазы, русское название)."""
    e = elongation_deg % 360.0
    if e < 12 or e >= 348:
        return "new", "Новолуние"
    if e < 78:
        return "waxing_crescent", "Растущий серп"
    if e < 102:
        return "first_quarter", "Первая четверть"
    if e < 168:
        return "waxing_gibbous", "Растущая Луна"
    if e < 192:
        return "full", "Полнолуние"
    if e < 258:
        return "waning_gibbous", "Убывающая Луна"
    if e < 282:
        return "last_quarter", "Последняя четверть"
    return "waning_crescent", "Убывающий серп"


def _libra_aspect_from_moon_index(moon_idx: int) -> tuple[str, str]:
    """Определяет аспект Луны к знаку Весы (индекс 6)."""
    diff = (moon_idx - 6) % 12
    if diff == 0:
        return (
            "Луна в Весах (соединение)",
            "максимальная личная сила, обострённое обаяние и фокус на собственных желаниях",
        )
    if diff in (4, 8):
        return (
            "Трин по стихии Воздуха",
            "лёгкость в общении, удачные переговоры, свежие идеи и прилив вдохновения",
        )
    if diff in (2, 10):
        return (
            "Секстиль возможностей",
            "мягкая поддержка дня: полезные знакомства, приятные новости и дипломатичные решения",
        )
    if diff in (3, 9):
        return (
            "Квадратура (точка роста)",
            "проверка личных границ: не соглашайтесь на чужую суету и берегите внутренний баланс",
        )
    if diff == 6:
        return (
            "Оппозиция в Овне (ось партнёрства)",
            "яркая динамика с людьми: важно слышать себя, но не рубить с плеча в спорах",
        )
    return (
        "Гармоничная перестройка",
        "спокойный фон для внимательности к деталям, интуиции и бережного ритма",
    )


def load_history(history_path: Path) -> dict[str, Any]:
    if not history_path.exists():
        return {"used_tarot": [], "used_compat": [], "posts": []}
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        data.setdefault("used_tarot", [])
        data.setdefault("used_compat", [])
        data.setdefault("posts", [])
        return data
    except Exception:
        return {"used_tarot": [], "used_compat": [], "posts": []}


# Рубрики, где фигурирует партнёрский знак: для них общий антиповтор,
# иначе за один день «Весы × Лев» может выпасть трижды.
PAIRED_RUBRICS = {
    "love", "love_daily", "sex", "business",
    "month_love", "month_sex", "month_business",
}


def save_history(history_path: Path, history: dict[str, Any], ctx: DailyAstroContext, title: str) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if ctx.rubric_key == "tarot":
        used_tarot = [x for x in history.get("used_tarot", []) if x != ctx.tarot_card["id"]]
        used_tarot.append(ctx.tarot_card["id"])
        history["used_tarot"] = used_tarot[-14:]
    if ctx.rubric_key in PAIRED_RUBRICS:
        used_compat = [x for x in history.get("used_compat", []) if x != ctx.compat_partner["sign"]]
        used_compat.append(ctx.compat_partner["sign"])
        history["used_compat"] = used_compat[-6:]

    posts = history.get("posts", [])
    posts.append(
        {
            "date": ctx.date_iso,
            "slot": ctx.slot,
            "rubric": ctx.rubric_key,
            "title": title[:120],
        }
    )
    history["posts"] = posts[-60:]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def choose_rubric(slot: str, weekday_index: int, day_of_month: int = 1, month_last_day: int = 31) -> str:
    """Выбирает рубрику по слоту, дню недели и (для месячных) последнему дню месяца."""
    s = slot.lower().strip()

    # В последний календарный день месяца тематические слоты
    # превращаются в месячные прогнозы на СЛЕДУЮЩИЙ месяц.
    # ЭТА ПРОВЕРКА ИДЁТ ПЕРВОЙ — иначе алиасы из RUBRICS её перекроют.
    if day_of_month == month_last_day:
        month_slot_map = {
            "sex": "month_sex",
            "love": "month_love",
            "love_daily": "month_love",
            "business": "month_business",
            "evening": "month_love",
        }
        if s in month_slot_map:
            return month_slot_map[s]

    # «love» — это ежедневная рубрика «Любовь с Весами» (алиас love_daily)
    if s == "love":
        return "love_daily"

    if s == "pulse":
        return "pulse"

    if s in RUBRICS:
        return s

    if s == "morning":
        return "forecast"

    if s == "day":
        return "tarot" if weekday_index % 2 == 0 else "venus"

    if s == "sex":
        return "sex"

    if s in ("love", "love_daily"):
        return "love_daily"

    if s == "business":
        return "business"

    if s == "moon":
        return "moon_today"



    if s == "evening":
        # Секс/Любовь/Бизнес выходят ЕЖЕДНЕВНО отдельными слотами,
        # поэтому вечерняя ротация отдана «атмосферным» форматам.
        evening_map = {
            0: "pulse",        # Пн — «Весы за 15 секунд»
            1: "tarot",        # Вт — карта дня
            2: "quiz",         # Ср — тест «Какой вы Весы?»
            3: "pulse",        # Чт — «Весы за 15 секунд»
            4: "tarot",        # Пт — карта дня
            5: "week_ahead",   # Сб — фокус на неделю
            6: "venus",        # Вс — совет Венеры
        }
        return evening_map.get(weekday_index, "tarot")

    return "forecast"


def _pick_from_pool(pool: list[dict[str, str]], used_ids: list[str], key_field: str, seed_str: str) -> dict[str, str]:
    available = [item for item in pool if item[key_field] not in used_ids]
    candidates = available if available else pool
    digest = hashlib.sha256(seed_str.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") % len(candidates)
    return candidates[idx]


def build_daily_context(
    now_utc: datetime | None = None,
    tz_offset_hours: int = 3,
    slot: str = "morning",
    history_path: Path | None = None,
) -> DailyAstroContext:
    """Вычисляет полные астрологические данные на день для Весов."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    tz = timezone(timedelta(hours=tz_offset_hours))
    local_dt = now_utc.astimezone(tz)

    # Для стабильных суточных показателей используем полдень локального дня
    noon_local = local_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    noon_utc = noon_local.astimezone(timezone.utc)
    jd = _julian_day(noon_utc)
    T = (jd - 2451545.0) / 36525.0

    # Тропическая долгота Солнца (Meeus Ch. 25)
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360.0
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360.0
    M_rad = math.radians(M)
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
        + (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
        + 0.000289 * math.sin(3 * M_rad)
    )
    sun_lon = (L0 + C) % 360.0

    # Тропическая долгота Луны (Meeus Ch. 47, основные гармоники)
    Lp = (218.3164477 + 481267.88123421 * T - 0.0015786 * T * T) % 360.0
    D = (297.8501921 + 445267.1114034 * T - 0.0018819 * T * T) % 360.0
    Ms = (357.5291092 + 35999.0502909 * T - 0.0001536 * T * T) % 360.0
    Mm = (134.9633964 + 477198.8675055 * T + 0.0087414 * T * T) % 360.0
    F = (93.2720950 + 483202.0175233 * T - 0.0036539 * T * T) % 360.0

    Dr, Msr, Mmr, Fr = map(math.radians, (D, Ms, Mm, F))
    moon_lon = (
        Lp
        + 6.288774 * math.sin(Mmr)
        + 1.274027 * math.sin(2 * Dr - Mmr)
        + 0.658314 * math.sin(2 * Dr)
        + 0.213618 * math.sin(2 * Mmr)
        - 0.185116 * math.sin(Msr)
        - 0.114332 * math.sin(2 * Fr)
        + 0.058793 * math.sin(2 * Dr - 2 * Mmr)
        + 0.057066 * math.sin(2 * Dr - Msr - Mmr)
        + 0.053322 * math.sin(2 * Dr + Mmr)
        + 0.045758 * math.sin(2 * Dr - Msr)
        - 0.040923 * math.sin(Msr - Mmr)
        - 0.034720 * math.sin(Dr)
        - 0.030383 * math.sin(Msr + Mmr)
        + 0.015327 * math.sin(2 * Dr - 2 * Fr)
    ) % 360.0

    elongation = (moon_lon - sun_lon) % 360.0
    illumination = round((1.0 - math.cos(math.radians(elongation))) / 2.0 * 100.0, 1)
    age_days = round(elongation / 360.0 * 29.530588853, 2)
    lunar_day = max(1, min(30, int(age_days) + 1))

    phase_key, phase_name = _moon_phase_info(elongation)

    sun_idx = int(sun_lon // 30) % 12
    moon_idx = int(moon_lon // 30) % 12
    sun_sign, _, _ = ZODIAC_SIGNS[sun_idx]
    moon_sign, moon_element, moon_symbol = ZODIAC_SIGNS[moon_idx]

    weekday_idx = local_dt.weekday()
    weekday_name = WEEKDAYS_RU[weekday_idx]
    planet_ruler, planet_theme = WEEKDAY_RULERS[weekday_idx]

    date_iso = local_dt.strftime("%Y-%m-%d")
    date_human = f"{local_dt.day} {MONTHS_GENITIVE[local_dt.month]}"

    libra_aspect, libra_aspect_tone = _libra_aspect_from_moon_index(moon_idx)

    # Детерминированные суточные показатели (от 3 до 5, зависят от даты и аспекта)
    seed_bytes = hashlib.sha256(f"libra-{date_iso}".encode("utf-8")).digest()
    base_bonus = 1 if moon_element in ("Воздух", "Огонь") else 0
    love_score = min(5, 3 + ((seed_bytes[0] + (1 if weekday_idx == 4 else 0)) % 3))
    career_score = min(5, 3 + ((seed_bytes[1] + base_bonus) % 3))
    energy_score = min(5, 3 + (seed_bytes[2] % 3))
    lucky_number = 1 + (seed_bytes[3] % 29)
    lucky_color = LUCKY_COLORS[seed_bytes[4] % len(LUCKY_COLORS)]
    lucky_stone = STONES_OF_DAY[seed_bytes[5] % len(STONES_OF_DAY)]
    start_h = 10 + (seed_bytes[6] % 9)
    lucky_hours = f"{start_h:02d}:00–{start_h + 2:02d}:00"

    # Последний календарный день месяца -> месячные прогнозы
    next_month = local_dt.month % 12 + 1
    next_year = local_dt.year + (1 if local_dt.month == 12 else 0)
    month_last_day = calendar.monthrange(local_dt.year, local_dt.month)[1]
    is_month_end = local_dt.day == month_last_day
    # Месяц, НА который делается прогноз: если сегодня последний день — следующий месяц
    target_month = next_month if is_month_end else local_dt.month

    rubric_key = choose_rubric(slot, weekday_idx, local_dt.day, month_last_day)
    rubric_meta = RUBRICS[rubric_key]

    # Тип Весов для рубрики-теста (детерминированно по дате)
    libra_type = LIBRA_TYPES[seed_bytes[7] % len(LIBRA_TYPES)] if rubric_key == "quiz" else None

    history = load_history(history_path) if history_path else {"used_tarot": [], "used_compat": []}
    tarot_card = _pick_from_pool(
        TAROT_DECK,
        history.get("used_tarot", []),
        "id",
        f"tarot-{date_iso}-{slot}",
    )
    compat_partner = _pick_from_pool(
        COMPATIBILITY_PROFILES,
        history.get("used_compat", []),
        "sign",
        f"compat-{date_iso}-{slot}",
    )

    return DailyAstroContext(
        date_iso=date_iso,
        date_human=date_human,
        weekday_name=weekday_name,
        weekday_index=weekday_idx,
        planet_ruler=planet_ruler,
        planet_theme=planet_theme,
        sun_sign=sun_sign,
        sun_degree=round(sun_lon % 30, 1),
        moon_sign=moon_sign,
        moon_sign_locative=ZODIAC_LOCATIVE[moon_sign],
        moon_symbol=moon_symbol,
        moon_element=moon_element,
        moon_degree=round(moon_lon % 30, 1),
        moon_phase_key=phase_key,
        moon_phase_name=phase_name,
        moon_illumination=illumination,
        moon_age_days=age_days,
        lunar_day=lunar_day,
        libra_aspect=libra_aspect,
        libra_aspect_tone=libra_aspect_tone,
        love_score=love_score,
        career_score=career_score,
        energy_score=energy_score,
        lucky_number=lucky_number,
        lucky_color=lucky_color,
        lucky_stone=lucky_stone,
        lucky_hours=lucky_hours,
        slot=slot,
        rubric_key=rubric_key,
        rubric_badge=rubric_meta["badge"],
        card_theme=rubric_meta["card_theme"],
        rubric_emoji=rubric_meta["emoji"],
        rubric_hashtag=rubric_meta["hashtag"],
        tarot_card=tarot_card,
        compat_partner=compat_partner,
        day_of_month=local_dt.day,
        month_last_day=month_last_day,
        is_month_end=is_month_end,
        target_month=target_month,
        target_month_name=month_number_ru(target_month),
        target_month_genitive=month_genitive_ru(target_month),
        libra_type=libra_type,
    )
