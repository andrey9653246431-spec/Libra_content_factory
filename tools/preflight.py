"""Диагностика настроек перед запуском автопостинга.

Проверяет токен бота, права в канале, режим публикации, провайдера ИИ и ресурсы.

Запуск (из корня проекта):
    python -m tools.preflight
    python -m tools.preflight --test-llm
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.llm_client import _detect_provider  # noqa: E402

OK = "✅"
WARN = "⚠️"
FAIL = "❌"

problems: list[str] = []
warnings: list[str] = []


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _mask(value: str) -> str:
    if len(value) <= 10:
        return value[:2] + "…"
    return f"{value[:6]}…{value[-4:]}"


def _tg(method: str, token: str, params: dict | None = None) -> dict:
    resp = requests.get(f"https://api.telegram.org/bot{token}/{method}", params=params or {}, timeout=20)
    return resp.json()


def check_bot_token() -> str | None:
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    if not token:
        problems.append("TG_BOT_TOKEN не задан")
        print(f"{FAIL} TG_BOT_TOKEN: не задан")
        return None

    if ":" not in token:
        problems.append("TG_BOT_TOKEN имеет неверный формат (нет двоеточия)")
        print(f"{FAIL} TG_BOT_TOKEN: неверный формат — ожидается вида 1234567890:AAF...")
        return None

    try:
        payload = _tg("getMe", token)
    except requests.RequestException as exc:
        problems.append(f"Нет связи с api.telegram.org: {exc}")
        print(f"{FAIL} TG_BOT_TOKEN: нет связи с Telegram API ({exc})")
        return None

    if not payload.get("ok"):
        problems.append(f"Telegram отклонил токен: {payload.get('description')}")
        print(f"{FAIL} TG_BOT_TOKEN ({_mask(token)}): Telegram отклонил — {payload.get('description')}")
        if payload.get("error_code") == 401:
            print("     ↳ Токен неверный или отозван в @BotFather (/revoke). Создайте новый: /mybots → API Token.")
        return None

    bot = payload["result"]
    print(f"{OK} Бот найден: @{bot.get('username')} (id {bot.get('id')}), токен {_mask(token)}")
    return bot.get("username")


def check_channel(bot_username: str | None) -> None:
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    channel = os.getenv("TG_CHANNEL_ID", "").strip()
    if not token:
        return
    if not channel:
        problems.append("TG_CHANNEL_ID не задан")
        print(f"{FAIL} TG_CHANNEL_ID: не задан")
        return

    if channel.startswith("https://t.me/"):
        warnings.append("TG_CHANNEL_ID указан ссылкой — используйте @username или -100...")
        print(f"{WARN} TG_CHANNEL_ID выглядит как ссылка. Нужно @username или -1001234567890")

    try:
        payload = _tg("getChat", token, {"chat_id": channel})
    except requests.RequestException as exc:
        problems.append(f"Нет связи с Telegram API: {exc}")
        print(f"{FAIL} TG_CHANNEL_ID: нет связи с Telegram API")
        return

    if not payload.get("ok"):
        desc = payload.get("description", "")
        problems.append(f"Канал недоступен боту: {desc}")
        print(f"{FAIL} TG_CHANNEL_ID ({channel}): {desc}")
        if "chat not found" in desc.lower():
            print("     ↳ Причины: (1) бот не добавлен в канал; (2) неверный @username;")
            print("        (3) канал закрытый → нужен числовой id вида -100…; (4) канал удалён.")
            print("     ↳ Как узнать id закрытого канала: перешлите любой пост из канала боту @getidsbot")
            print("        или временно добавьте бота и вызовите getUpdates (см. templates/GITHUB_SETUP.md).")
        if "member" in desc.lower() or payload.get("error_code") == 403:
            print("     ↳ Бот не участник канала — добавьте его администратором с правом публикации.")
        return

    chat = payload["result"]
    title = chat.get("title") or chat.get("username")
    print(f"{OK} Канал найден: «{title}» (id {chat.get('id')}, тип {chat.get('type')})")

    if chat.get("type") != "channel":
        warnings.append("TG_CHANNEL_ID указывает не на канал")
        print(f"{WARN} Это не канал, а {chat.get('type')}. Для публикации постов нужен канал.")

    if not bot_username:
        return

    try:
        member = _tg("getChatMember", token, {"chat_id": channel, "user_id": _bot_id(token)})
        if not member.get("ok"):
            problems.append("Бот не добавлен в канал")
            print(f"{FAIL} Бот не найден среди участников канала — добавьте его администратором")
            print("     ↳ Канал → Управление каналом → Администраторы → Добавить администратора")
            return
        res = member.get("result", {})
        status = res.get("status")
        if status in ("administrator", "creator"):
            can_post = res.get("can_post_messages", True)
            if can_post:
                print(f"{OK} Бот — администратор канала с правом публикации")
            else:
                problems.append("У бота отключено право can_post_messages")
                print(f"{FAIL} Бот админ, но право «Публикация сообщений» выключено — включите его")
        else:
            problems.append(f"Бот в канале со статусом {status}, нужен administrator")
            print(f"{FAIL} Бот не администратор (статус: {status}) — добавьте его в администраторы канала")
    except requests.RequestException:
        warnings.append("Не удалось проверить права бота в канале")
        print(f"{WARN} Не удалось проверить права бота в канале")


def _bot_id(token: str) -> int:
    try:
        return int(token.split(":", 1)[0])
    except (ValueError, IndexError):
        return 0


def check_publish_mode() -> None:
    mode = os.getenv("PUBLISH_MODE", "auto").strip().lower()
    admin_id = os.getenv("TG_ADMIN_ID", "").strip()
    if mode not in ("auto", "draft"):
        warnings.append(f"PUBLISH_MODE={mode} неизвестен, будет использован auto")
        print(f"{WARN} PUBLISH_MODE={mode}: допустимо только auto или draft")
        return
    if mode == "draft":
        if admin_id:
            print(f"{OK} Режим draft: черновики уйдут в личку {admin_id}")
        else:
            warnings.append("PUBLISH_MODE=draft, но TG_ADMIN_ID пуст — посты пойдут в канал")
            print(f"{WARN} Режим draft без TG_ADMIN_ID: посты пойдут прямо в канал")
    else:
        print(f"{OK} Режим публикации: auto (сразу в канал)")


def check_llm(test_request: bool = False) -> None:
    provider = _detect_provider()
    if not provider:
        print(f"{WARN} Ключи ИИ не заданы — будет использован встроенный офлайн-генератор (работает всегда)")
        return
    print(f"{OK} Провайдер ИИ: {provider['name']}, модель {provider['model']}")
    if not test_request:
        return

    print("     ↳ Отправляю тестовый запрос к модели…")
    try:
        resp = requests.post(
            provider["url"],
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider["model"],
                "messages": [{"role": "user", "content": "Ответь одним словом: работает"}],
                "max_tokens": 16,
            },
            timeout=45,
        )
        if resp.status_code == 200:
            print(f"{OK} Модель ответила — ключ рабочий")
        elif resp.status_code in (401, 403):
            problems.append(f"Ключ ИИ отклонён провайдером {provider['name']} ({resp.status_code})")
            print(f"{FAIL} Ключ ИИ отклонён ({resp.status_code}). Проверьте, что ключ скопирован полностью и активен")
        elif resp.status_code == 429:
            warnings.append("Лимит бесплатного тарифа исчерпан")
            print(f"{WARN} Превышен лимит бесплатного тарифа (429). Завод продолжит работу на офлайн-генераторе")
        else:
            warnings.append(f"Провайдер {provider['name']} вернул {resp.status_code}")
            print(f"{WARN} Ответ {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as exc:
        warnings.append(f"Сеть недоступна для LLM: {exc}")
        print(f"{WARN} Запрос к модели не выполнен: {exc}")


def check_assets() -> None:
    avatar = BASE_DIR / "assets" / "libra_avatar.png"
    if avatar.exists():
        print(f"{OK} Аватарка канала на месте: assets/libra_avatar.png")
    else:
        warnings.append("assets/libra_avatar.png отсутствует")
        print(f"{WARN} assets/libra_avatar.png отсутствует (на генерацию карточек не влияет)")

    hist = BASE_DIR / "data" / "history.json"
    if hist.exists():
        print(f"{OK} История антиповтора: data/history.json")
    else:
        warnings.append("data/history.json отсутствует — будет создан автоматически")
        print(f"{WARN} data/history.json отсутствует (будет создан автоматически)")

    try:
        import PIL  # noqa: F401

        print(f"{OK} Pillow установлен — карточки будут генерироваться")
    except ImportError:
        problems.append("Pillow не установлен")
        print(f"{FAIL} Pillow не установлен — выполните: pip install -r requirements.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка настроек контент-завода Весы")
    parser.add_argument("--test-llm", action="store_true", help="Сделать реальный тестовый запрос к модели ИИ")
    args = parser.parse_args()

    _load_dotenv()
    print("=" * 62)
    print(" ДИАГНОСТИКА КОНТЕНТ-ЗАВОДА «ВЕСЫ»")
    print("=" * 62)
    print("\n[1/5] Telegram-бот")
    bot_username = check_bot_token()

    print("\n[2/5] Канал и права бота")
    if bot_username:
        check_channel(bot_username)
    else:
        print("⏭️  Пропущено: сначала нужен рабочий TG_BOT_TOKEN (проверьте его в секретах репозитория)")

    print("\n[3/5] Режим публикации")
    check_publish_mode()

    print("\n[4/5] Генератор текста")
    check_llm(test_request=args.test_llm)

    print("\n[5/5] Ресурсы проекта")
    check_assets()

    print("\n" + "=" * 62)
    if problems:
        print(f"{FAIL} НАЙДЕНО ПРОБЛЕМ: {len(problems)}")
        for i, p in enumerate(problems, 1):
            print(f"   {i}. {p}")
        print("   Исправьте их и запустите диагностику снова.")
        print("=" * 62)
        return 1
    if warnings:
        print(f"{WARN} Готово с предупреждениями ({len(warnings)}). Публикация возможна.")
        for w in warnings:
            print(f"   • {w}")
    else:
        print(f"{OK} ВСЁ ГОТОВО — можно публиковать!")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
