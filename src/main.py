"""Главный сценарий запуска бесплатного контент-завода для канала Весы."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.astro_engine import build_daily_context, load_history, save_history
from src.card_generator import render_daily_card
from src.llm_client import generate_post_content
from src.telegram_publisher import publish_to_telegram

BASE_DIR = Path(__file__).resolve().parent.parent
VERBOSE = os.getenv("VERBOSE", "").strip() in ("1", "true", "yes")


def log(msg: str) -> None:
    """Печать только при VERBOSE=1 (по умолчанию лог остаётся чистым)."""
    if VERBOSE:
        print(msg, flush=True)


def _load_dotenv_if_present(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _infer_slot_by_hour(tz_offset_hours: int) -> str:
    from datetime import timedelta

    now_local = datetime.now(timezone.utc) + timedelta(hours=tz_offset_hours)
    h = now_local.hour
    if h < 12:
        return "morning"
    if h < 17:
        return "day"
    return "evening"


def run_pipeline(
    slot: str = "auto",
    dry_run: bool = False,
    force_offline: bool = False,
    no_image: bool = False,
    date_override: str | None = None,
) -> dict:
    _load_dotenv_if_present(BASE_DIR / ".env")

    tz_offset = int(os.getenv("TIMEZONE_OFFSET", "3"))
    channel_handle = os.getenv("CHANNEL_HANDLE", "@vesy_prognoz").strip()

    now_utc = datetime.now(timezone.utc)
    if date_override:
        now_utc = datetime.strptime(date_override, "%Y-%m-%d").replace(hour=9, tzinfo=timezone.utc)

    resolved_slot = _infer_slot_by_hour(tz_offset) if slot == "auto" else slot
    history_path = BASE_DIR / "data" / "history.json"

    log(f"[1/5] Расчёт астроданых: слот={resolved_slot}, дата={now_utc.date()}")
    ctx = build_daily_context(
        now_utc=now_utc,
        tz_offset_hours=tz_offset,
        slot=resolved_slot,
        history_path=history_path,
    )

    log(f"[2/5] Генерация текста: провайдер={'offline' if force_offline else 'auto'}")
    content = generate_post_content(
        ctx=ctx,
        channel_handle=channel_handle,
        force_offline=force_offline,
    )

    log(f"[3/5] Рендер карточки: {ctx.rubric_key}")
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    card_path: Path | None = None

    if not no_image:
        card_filename = f"card_{ctx.date_iso}_{ctx.rubric_key}.png"
        card_path = render_daily_card(
            ctx=ctx,
            headline=content["card_headline"],
            subline=content["card_subline"],
            output_path=output_dir / card_filename,
            channel_handle=channel_handle,
        )

    result_record = {
        "date": ctx.date_iso,
        "slot": resolved_slot,
        "rubric": ctx.rubric_key,
        "source": content["source"],
        "title": content["title"],
        "card_headline": content["card_headline"],
        "card_subline": content["card_subline"],
        "card_path": str(card_path) if card_path else None,
        "post_html": content["post_html"],
        "astro": ctx.to_dict(),
    }
    (output_dir / "last_post.json").write_text(
        json.dumps(result_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if dry_run:
        result_record["published"] = False
        result_record["mode"] = "dry_run"
        return result_record

    log(f"[4/5] Публикация: channel={os.getenv('TG_CHANNEL_ID', '')!r}, "
        f"mode={os.getenv('PUBLISH_MODE', 'auto')!r}, "
        f"token={'задан' if os.getenv('TG_BOT_TOKEN') else 'НЕ ЗАДАН'}, "
        f"caption_len={len(content['post_html'])}")
    tg_resp = publish_to_telegram(
        text_html=content["post_html"],
        image_path=card_path,
    )
    history = load_history(history_path)
    save_history(history_path, history, ctx, content["title"])

    log("[5/5] История антиповтора обновлена")
    result_record["published"] = True
    result_record["telegram_message_id"] = tg_resp.get("result", {}).get("message_id")
    return result_record


def main() -> int:
    global VERBOSE
    parser = argparse.ArgumentParser(description="Бесплатный контент-завод для Telegram-канала Весы")
    parser.add_argument(
        "--slot",
        default=os.getenv("POST_SLOT", "auto"),
        choices=["auto", "morning", "day", "evening", "forecast", "tarot", "love", "venus", "week_ahead"],
        help="Слот или конкретная рубрика поста",
    )
    parser.add_argument("--dry-run", action="store_true", help="Сгенерировать пост и картинку без отправки в Telegram")
    parser.add_argument("--offline", action="store_true", help="Принудительно использовать встроенный офлайн-генератор")
    parser.add_argument("--no-image", action="store_true", help="Не генерировать PNG-карточку")
    parser.add_argument("--date", default=None, help="Переопределить дату YYYY-MM-DD (для теста)")
    parser.add_argument("--verbose", action="store_true", help="Подробный лог по этапам")
    args = parser.parse_args()
    if args.verbose:
        VERBOSE = True

    # CHANNEL_HANDLE вида @username может заменить TG_CHANNEL_ID
    _handle = os.getenv("CHANNEL_HANDLE", "").strip()
    if not os.getenv("TG_CHANNEL_ID", "").strip() and _handle.startswith("@"):
        os.environ["TG_CHANNEL_ID"] = _handle

    # Мгновенная и понятная ошибка до расчётов
    if not args.dry_run:
        missing = [k for k in ("TG_BOT_TOKEN", "TG_CHANNEL_ID") if not os.getenv(k, "").strip()]
        if missing:
            print("❌ Не заданы секреты: " + ", ".join(missing), file=sys.stderr)
            print("::error::Не заданы секреты: " + ", ".join(missing), file=sys.stderr)
            print("   Settings → Secrets and variables → Actions → вкладка Secrets", file=sys.stderr)
            print("   Подсказка: можно задать только TG_BOT_TOKEN, а канал — в Variables CHANNEL_HANDLE=@username", file=sys.stderr)
            return 1

    try:
        res = run_pipeline(
            slot=args.slot,
            dry_run=args.dry_run,
            force_offline=args.offline,
            no_image=args.no_image,
            date_override=args.date,
        )
    except Exception as exc:  # noqa: BLE001
        print("", file=sys.stderr)
        print("=" * 62, file=sys.stderr)
        print("❌ ГЕНЕРАЦИЯ/ПУБЛИКАЦИЯ НЕ УДАЛАСЬ", file=sys.stderr)
        print(f"   {type(exc).__name__}: {exc}", file=sys.stderr)
        print("-" * 62, file=sys.stderr)

        missing = [k for k in ("TG_BOT_TOKEN", "TG_CHANNEL_ID") if not os.getenv(k, "").strip()]
        if missing:
            print("   Причина: не заданы переменные окружения/секреты:", file=sys.stderr)
            for m in missing:
                print(f"     • {m}", file=sys.stderr)
            print("   Где добавить: Settings → Secrets and variables → Actions → Secrets", file=sys.stderr)
            print("   Затем: Actions → Check Setup (diagnostics) → Run workflow", file=sys.stderr)
        else:
            print("   Проверьте права бота в канале и правильность TG_CHANNEL_ID:", file=sys.stderr)
            print(f"     TG_CHANNEL_ID = {os.getenv('TG_CHANNEL_ID')}", file=sys.stderr)
            print("   Диагностика: Actions → Check Setup (diagnostics)", file=sys.stderr)
        print("=" * 62, file=sys.stderr)
        return 1

    if res.get("published") is False and not args.dry_run:
        print("[!] Пост не отправлен: сработал резервный режим", file=sys.stderr)
    print(f"[OK] Дата: {res['date']} | Рубрика: {res['rubric']} | Источник: {res['source']}")
    print(f"[OK] Заголовок: {res['title']}")
    if res.get("card_path"):
        print(f"[OK] Карточка: {res['card_path']}")
    print(f"[OK] Опубликовано в Telegram: {res.get('published')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
