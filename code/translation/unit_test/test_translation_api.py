# tests/test_translation_api.py

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import translation_api module from code directory
from code.translation.translation_api import (
    TranslatorAPI,
    save_translations_jsonl,
    load_translations_jsonl,
)


class TestTranslatorAPI(unittest.TestCase):
    @patch("code.translation_api.genai.Client")
    def test_translate_single_text(self, MockClient):
        # Arrange: mock Gemini client and response
        mock_client = MockClient.return_value
        mock_response = MagicMock()
        mock_response.text = "Hallo Welt"
        mock_client.models.generate_content.return_value = mock_response

        api = TranslatorAPI(api_key="dummy-key", model_name="gemini-2.5-flash")

        # Act
        out = api.translate("Hello world", src="en", tgt="de")

        # Assert
        self.assertEqual(out, "Hallo Welt")
        mock_client.models.generate_content.assert_called_once()
        args, kwargs = mock_client.models.generate_content.call_args
        self.assertIn("gemini-2.5-flash", kwargs["model"])

    @patch("code.translation_api.genai.Client")
    def test_translate_segments_in_place(self, MockClient):
        # Mock client similar to above
        mock_client = MockClient.return_value
        mock_response_1 = MagicMock()
        mock_response_1.text = "Hallo"
        mock_response_2 = MagicMock()
        mock_response_2.text = "Welt"

        # Return different results for each generate_content call
        mock_client.models.generate_content.side_effect = [mock_response_1, mock_response_2]

        api = TranslatorAPI(api_key="dummy-key", model_name="gemini-2.5-flash")

        segments = [
            {"index": 1, "start": timedelta(seconds=0), "end": timedelta(seconds=1), "text_en": "Hello"},
            {"index": 2, "start": timedelta(seconds=1), "end": timedelta(seconds=2), "text_en": "World"},
        ]

        out_segments = api.translate_segments(segments, src="en", tgt="de")

        self.assertEqual(out_segments[0]["text_de"], "Hallo")
        self.assertEqual(out_segments[1]["text_de"], "Welt")
        self.assertEqual(len(mock_client.models.generate_content.call_args_list), 2)


class TestTranslationCache(unittest.TestCase):
    def test_save_and_load_translations_jsonl(self):
        segments = [
            {
                "index": 1,
                "start": timedelta(seconds=0),
                "end": timedelta(seconds=1.5),
                "text_en": "Hello",
                "text_de": "Hallo",
            },
            {
                "index": 2,
                "start": timedelta(seconds=1.5),
                "end": timedelta(seconds=3.0),
                "text_en": "world",
                "text_de": "Welt",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "translations.jsonl"

            # Save
            save_translations_jsonl(segments, path)
            self.assertTrue(path.exists())

            # Load
            loaded = load_translations_jsonl(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["index"], 1)
            self.assertAlmostEqual(loaded[0]["start_sec"], 0.0)
            self.assertAlmostEqual(loaded[0]["end_sec"], 1.5)
            self.assertEqual(loaded[0]["text_en"], "Hello")
            self.assertEqual(loaded[0]["text_de"], "Hallo")

            # Verify file is valid JSONL
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    json.loads(line)  # Should not raise exception


if __name__ == "__main__":
    unittest.main()

'''
# run unit test
python -m code.translation.unit_test.test_translation_api
'''