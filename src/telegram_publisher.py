"""Публикация постов и карточек в Telegram через Bot API (бесплатно)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


def _post_telegram(method: str, bot_token: str, data: dict[str, Any], files: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    resp = requests.post(url, data=data, files=files, timeout=30)
    try:
        payload = resp.json()
    except Exception:
        resp.raise_for_status()
        raise RuntimeError(f"Некорректный ответ Telegram API: {resp.text[:300]}")

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error ({payload.get('error_code')}): {payload.get('description')}")
    return payload


def publish_to_telegram(
    text_html: str,
    image_path: Path | None = None,
    bot_token: str | None = None,
    channel_id: str | None = None,
    publish_mode: str | None = None,
    admin_id: str | None = None,
) -> dict[str, Any]:
    """Отправляет пост в канал или в черновик админу."""
    token = (bot_token or os.getenv("TG_BOT_TOKEN", "")).strip()
    mode = (publish_mode or os.getenv("PUBLISH_MODE", "auto")).strip().lower()
    target_channel = (channel_id or os.getenv("TG_CHANNEL_ID", "")).strip()
    target_admin = (admin_id or os.getenv("TG_ADMIN_ID", "")).strip()

    if not token:
        raise ValueError("Не задан TG_BOT_TOKEN")

    chat_id = target_admin if (mode == "draft" and target_admin) else target_channel
    if not chat_id:
        raise ValueError("Не задан TG_CHANNEL_ID (или TG_ADMIN_ID для режима draft)")

    prefix = "📝 <b>[ЧЕРНОВИК ДЛЯ ПРОВЕРКИ]</b>\n\n" if mode == "draft" else ""
    full_text = prefix + text_html

    if image_path and image_path.exists():
        # Лимит Telegram caption = 1024 символа
        if len(full_text) <= 1020:
            with image_path.open("rb") as f:
                data = {
                    "chat_id": chat_id,
                    "caption": full_text,
                    "parse_mode": "HTML",
                }
                return _post_telegram("sendPhoto", token, data=data, files={"photo": f})
        # Если с префиксом черновика чуть длиннее — отправляем фото + отдельным сообщением текст
        with image_path.open("rb") as f:
            _post_telegram("sendPhoto", token, data={"chat_id": chat_id}, files={"photo": f})

    data = {
        "chat_id": chat_id,
        "text": full_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    return _post_telegram("sendMessage", token, data=data)
