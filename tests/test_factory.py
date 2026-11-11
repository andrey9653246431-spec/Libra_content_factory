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
            for rubric in (
                "forecast", "tarot", "love", "venus", "week_ahead",
                "sex", "love_daily", "business", "quiz", "moon",
            ):
                ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot=rubric)
                post = generate_fallback_post(ctx, channel_handle="@libra_astra")
                self.assertLessEqual(len(post["post_html"]), 1024)
                card_file = render_daily_card(
                    ctx=ctx,
                    headline=post["card_headline"],
                    subline=post["card_subline"],
                    output_path=tmp_dir / f"{rubric}.png",
                    channel_handle="@libra_astra",
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


    def test_new_daily_rubrics_are_daily(self) -> None:
        """Секс / Любовь / Бизнес выходят каждый день, а не по дням недели."""
        from src.astro_engine import choose_rubric

        for weekday in range(7):
            self.assertEqual(choose_rubric("sex", weekday, 12, 30), "sex")
            self.assertEqual(choose_rubric("love", weekday, 12, 30), "love_daily")
            self.assertEqual(choose_rubric("business", weekday, 12, 30), "business")
            self.assertEqual(choose_rubric("moon", weekday, 12, 30), "moon_today")
            self.assertEqual(choose_rubric("quiz", weekday, 12, 30), "quiz")

    def test_month_end_turns_into_monthly_forecasts(self) -> None:
        """В последний день месяца тематические слоты → прогноз на следующий месяц."""
        from src.astro_engine import choose_rubric

        self.assertEqual(choose_rubric("love", 0, 30, 30), "month_love")
        self.assertEqual(choose_rubric("love_daily", 0, 30, 30), "month_love")
        self.assertEqual(choose_rubric("sex", 0, 30, 30), "month_sex")
        self.assertEqual(choose_rubric("business", 0, 30, 30), "month_business")
        self.assertEqual(choose_rubric("evening", 0, 30, 30), "month_love")
        # 29-е — ещё обычный день
        self.assertEqual(choose_rubric("sex", 0, 29, 30), "sex")

    def test_monthly_forecasts_target_next_month(self) -> None:
        dt = datetime(2026, 11, 30, 9, 0, tzinfo=timezone.utc)
        for slot, expected in (("love", "month_love"), ("sex", "month_sex"), ("business", "month_business")):
            ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot=slot)
            self.assertEqual(ctx.rubric_key, expected)
            self.assertTrue(ctx.is_month_end)
            self.assertEqual(ctx.target_month_name, "декабрь")

    def test_quiz_has_three_types(self) -> None:
        dt = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
        ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot="quiz")
        self.assertEqual(ctx.rubric_key, "quiz")
        self.assertIsNotNone(ctx.libra_type)
        post = generate_fallback_post(ctx, channel_handle="@libra_astra")
        for word in ("Дипломат", "Эстет", "Бунтарь"):
            self.assertIn(word, post["post_html"])
        self.assertIn("комментариях", post["post_html"])

    def test_moon_card_is_short(self) -> None:
        dt = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
        ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot="moon")
        self.assertEqual(ctx.rubric_key, "moon_today")
        post = generate_fallback_post(ctx, channel_handle="@libra_astra")
        self.assertLessEqual(len(post["post_html"]), 600)

    def test_paired_rubrics_do_not_repeat_partner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hpath = Path(tmp) / "history.json"
            dt = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
            signs = []
            for slot in ("love", "sex", "business"):
                ctx = build_daily_context(now_utc=dt, tz_offset_hours=3, slot=slot, history_path=hpath)
                save_history(hpath, load_history(hpath), ctx, "test")
                signs.append(ctx.compat_partner["sign"])
            self.assertEqual(len(set(signs)), len(signs))

    def test_month_digest_publishes_three_posts(self) -> None:
        from src.main import _run_month_digest

        code = _run_month_digest(dry_run=True, force_offline=True, date_override="2026-11-30")
        self.assertEqual(code, 0)
        # не последний день — тихий пропуск
        code2 = _run_month_digest(dry_run=True, force_offline=True, date_override="2026-11-11")
        self.assertEqual(code2, 0)

    def test_content_extras_have_no_typos(self) -> None:
        from src import content_extras

        text = Path(content_extras.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Вашmes", text)
        self.assertNotIn("Intensity", text)

    def test_dry_run_pipeline(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            res = run_pipeline(slot="tarot", dry_run=True, force_offline=True, date_override="2026-11-11")
            self.assertFalse(res["published"])
            self.assertEqual(res["rubric"], "tarot")
            self.assertTrue(Path(res["card_path"]).exists())


if __name__ == "__main__":
    unittest.main()
