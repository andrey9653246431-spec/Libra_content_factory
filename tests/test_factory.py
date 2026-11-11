"""Автотесты бесплатного контент-завода для канала Весы."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.astro_engine import build_daily_context, save_history, load_history
from src.card_generator import render_daily_card
from src.fallback_writer import generate_fallback_post
from src.llm_client import sanitize_telegram_html, generate_post_content
from src.main import run_pipeline


class ContentFactoryTests(unittest.TestCase):
    def test_astronomical_calculations_nov_11_2026(self) -> None:
        dt = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
        ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot="morning")
        self.assertEqual(ctx.date_iso, "2026-11-11")
        self.assertEqual(ctx.sun_sign, "Скорпион")
        self.assertEqual(ctx.moon_sign, "Стрелец")
        self.assertEqual(ctx.moon_phase_key, "waxing_crescent")
        self.assertTrue(1.0 <= ctx.moon_illumination <= 10.0)
        self.assertIn(ctx.lunar_day, (2, 3))

    def test_sanitize_telegram_html_respects_limit_and_tags(self) -> None:
        raw = "<p>Привет <strong>Весы</strong> & друзья!<br>Текст **жирный**</p><script>bad</script>"
        clean = sanitize_telegram_html(raw, max_len=200)
        self.assertIn("<b>Весы</b>", clean)
        self.assertIn("&amp;", clean)
        self.assertIn("<b>жирный</b>", clean)
        self.assertNotIn("<script>", clean)
        self.assertNotIn("<p>", clean)

        long_html = "<b>Заголовок</b>\n" + ("Очень важный прогноз для Весов на сегодняшний день. " * 30)
        trimmed = sanitize_telegram_html(long_html, max_len=300)
        self.assertLessEqual(len(trimmed), 300)
        self.assertTrue(trimmed.count("<b>") == trimmed.count("</b>"))

    def test_all_rubrics_fallback_and_cards(self) -> None:
        dt = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for rubric in ("forecast", "tarot", "love", "venus", "week_ahead"):
                ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot=rubric)
                post = generate_fallback_post(ctx, channel_handle="@vesy_prognoz")
                self.assertLessEqual(len(post["post_html"]), 1024)
                card_file = render_daily_card(
                    ctx=ctx,
                    headline=post["card_headline"],
                    subline=post["card_subline"],
                    output_path=tmp_dir / f"{rubric}.png",
                    channel_handle="@vesy_prognoz",
                )
                self.assertTrue(card_file.exists())
                with Image.open(card_file) as im:
                    self.assertEqual(im.size, (1080, 1350))

    def test_history_anti_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hpath = Path(tmp) / "history.json"
            dt1 = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
            ctx1 = build_daily_context(now_utc=dt1, slot="tarot", history_path=hpath)
            hist = load_history(hpath)
            save_history(hpath, hist, ctx1, "Test")
            ctx2 = build_daily_context(now_utc=dt1, slot="tarot", history_path=hpath)
            self.assertNotEqual(ctx1.tarot_card["id"], ctx2.tarot_card["id"])

    def test_dry_run_pipeline(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            res = run_pipeline(slot="tarot", dry_run=True, force_offline=True, date_override="2026-11-11")
            self.assertFalse(res["published"])
            self.assertEqual(res["rubric"], "tarot")
            self.assertTrue(Path(res["card_path"]).exists())


if __name__ == "__main__":
    unittest.main()
