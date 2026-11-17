"""Regression tests for 720p, credit caps, no duplicate generations and story continuity."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from studio.skill.engine import Studio, StudioError, price


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.studio = Studio(Path(self.tmp.name))
        self.project = self.studio.create("Quarta-feira às Oito", "Romance de época", "romance",
                                          daily_limit=50, episode_limit=50)["id"]
        self.studio.bible(self.project, [
            {"id": "CHAR01", "name": "Emily", "appearance": "cabelo curto preto",
             "voice": "voz feminina, calma, pt-BR", "wardrobe": "cardigan vinho"}
        ], [
            {"id": "SET01", "description": "sala de estar dos anos 1980"}
        ], "Três amigos escondem um segredo familiar")
        self.studio.episode(self.project, 1, "O reencontro", "Emily encontra um segredo", [
            {"summary": "Emily abre uma carta", "characters": ["CHAR01"],
             "location_id": "SET01", "continuity": "mesmo cardigan",
             "model": "veo-3.1-lite", "seconds": 8},
            {"summary": "Emily olha a janela", "characters": ["CHAR01"],
             "location_id": "SET01", "continuity": "mesma noite",
             "model": "omni-flash-1.2", "seconds": 8},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_model_720p_prices_and_restrictions(self):
        self.assertEqual(price("veo-3.1-lite", 8), 10)
        self.assertEqual(price("omni-flash-1.2", 8), 24)
        with self.assertRaises(StudioError):
            price("veo-3.1-fast", 8)
        with self.assertRaises(StudioError):
            price("veo-3.1-lite", 10)
        with self.assertRaises(StudioError):
            price("omni-flash-1.2", 15)
        with self.assertRaises(StudioError):
            price("veo-3.1-lite", 6, "ingredients_to_video")

    def test_full_story_bible_and_consistent_prompt(self):
        prompt = self.studio.prompt(self.project, "E001C001")
        self.assertEqual(prompt["resolution"], "720p")
        self.assertIn("Emily", prompt["prompt"])
        self.assertIn("cardigan vinho", prompt["prompt"])
        self.assertEqual(prompt["model"], "veo-3.1-lite")
        self.assertEqual(self.studio.status(self.project)["episodes"][0]["scenes"][0]["status"], "planned")

    def test_uncertain_disallows_duplicate_generation(self):
        self.studio.prepare(self.project, "E001C001")
        self.studio.record_submitted(self.project, "E001C001", 10, "Flow mostra geração enviada")
        with self.assertRaises(StudioError):
            self.studio.record_submitted(self.project, "E001C001", 10, "clicar de novo")
        with self.assertRaises(StudioError):
            self.studio.prepare(self.project, "E001C001")
        self.assertEqual(self.studio.status(self.project)["episodes"][0]["credits_committed"], 10)

    def test_no_second_scene_while_first_uncertain(self):
        self.studio.prepare(self.project, "E001C001")
        self.studio.record_submitted(self.project, "E001C001", 10, "Flow mostra geração enviada")
        self.studio.prepare(self.project, "E001C002")
        with self.assertRaisesRegex(StudioError, "outra cena"):
            self.studio.record_submitted(self.project, "E001C002", 24, "Flow mostra geração enviada")
        self.assertEqual(self.studio.status(self.project)["episodes"][0]["credits_committed"], 10)

    def test_episode_budget_and_cost_mismatch(self):
        self.studio.prepare(self.project, "E001C001")
        with self.assertRaisesRegex(StudioError, "difere"):
            self.studio.record_submitted(self.project, "E001C001", 100, "Flow cobra 100")
        self.studio.record_submitted(self.project, "E001C001", 10, "Flow mostra 10")
        self.studio.reconcile_not_charged(self.project, "E001C001", "usuário conferiu extrato e nenhuma cobrança")
        self.assertEqual(self.studio.status(self.project)["episodes"][0]["credits_committed"], 0)

    def test_daily_limit_is_internal_not_model_supplied(self):
        self.studio.prepare(self.project, "E001C001")
        self.studio.record_submitted(self.project, "E001C001", 10, "cobrança confirmada")
        self.studio.reconcile_not_charged(self.project, "E001C001", "não houve cobrança")
        self.studio.prepare(self.project, "E001C001")
        self.studio.record_submitted(self.project, "E001C001", 10, "nova tentativa cobrada")
        self.studio.import_clip  # A clip not yet downloaded, so cannot advance to next submitted.
        self.assertEqual(self.studio.status(self.project)["episodes"][0]["credits_committed"], 10)

    def test_720p_import_strict(self):
        src = Path(self.tmp.name) / "clip.mp4"
        src.write_bytes(b"video placeholder")
        self.studio.prepare(self.project, "E001C001")
        with patch.object(Studio, "_probe", return_value=(640, 360)):
            with self.assertRaisesRegex(StudioError, "720p nativo"):
                self.studio.import_clip(self.project, "E001C001", str(src))
        with patch.object(Studio, "_probe", return_value=(1280, 720)):
            result = self.studio.import_clip(self.project, "E001C001", str(src))
        self.assertEqual(result["resolution"], "720p")
        self.assertTrue(Path(result["file"]).exists())
        self.studio.review(self.project, "E001C001", approve=True)
        self.assertEqual(self.studio.status(self.project)["episodes"][0]["scenes"][0]["status"], "approved")

    def test_no_overwrite_or_invalid_character(self):
        with self.assertRaises(StudioError):
            self.studio.episode(self.project, 1, "Repetido", "sinopse", [
                {"summary": "teste", "characters": []}
            ])
        with self.assertRaises(StudioError):
            self.studio.episode(self.project, 2, "Outro", "sinopse", [
                {"summary": "teste", "characters": ["BAD"]}
            ])

    def test_no_assembly_until_all_approved(self):
        with self.assertRaisesRegex(StudioError, "TODOS"):
            self.studio.assemble(self.project, 1)


if __name__ == "__main__":
    unittest.main()
