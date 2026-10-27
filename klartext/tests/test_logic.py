"""Tests der Logik ohne Mikrofon und Oberfläche: python -m unittest discover -s tests"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cleanup
import llm
import pipeline
from history import History
from hotkey import KeyBinding, PushToTalk, display_name, is_suitable_key, is_valid_key, key_name, normalise_key_name
from settings import Settings, load_api_key, save_api_key
from single_instance import SingleInstance
from version import app_version


class CleanupTest(unittest.TestCase):
    def test_german_fillers_and_comma(self):
        self.assertEqual(
            cleanup.clean("Ähm, ich glaube, äh, dass wir morgen kommen.", "de"),
            "Ich glaube, dass wir morgen kommen.",
        )

    def test_german_um_is_kept(self):
        self.assertEqual(cleanup.clean("Wir treffen uns um zehn Uhr.", "de"), "Wir treffen uns um zehn Uhr.")

    def test_english_fillers_and_repetition(self):
        self.assertEqual(
            cleanup.clean("the the launch is um uh gonna slip", "en"), "The launch is gonna slip"
        )

    def test_repetition_german(self):
        self.assertEqual(cleanup.clean("ich ich möchte das das Buch", "de"), "Ich möchte das Buch")

    def test_spacing_and_sentence_start(self):
        self.assertEqual(cleanup.clean("hallo , wie geht's ?  gut. danke", "de"), "Hallo, wie geht's? Gut. Danke")

    def test_dictionary_and_snippets(self):
        text = cleanup.clean(
            "ich nutze claude code und schicke meine mail",
            "de",
            dictionary={"claude code": "Claude Code"},
            snippets={"meine mail": "max@example.com"},
        )
        self.assertEqual(text, "Ich nutze Claude Code und schicke max@example.com")

    def test_dictionary_matches_whole_words_only(self):
        self.assertEqual(cleanup.apply_replacements("Katze katzen", {"katze": "Tiger"}), "Tiger katzen")

    def test_auto_language_uses_safe_fillers_only(self):
        self.assertEqual(cleanup.clean("wir treffen uns um acht äh", None), "Wir treffen uns um acht")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class LlmTest(unittest.TestCase):
    def test_request_has_key_model_and_wrapped_text(self):
        seen = {}

        def opener(request, timeout):
            seen["headers"] = {k.lower(): v for k, v in request.header_items()}
            seen["body"] = json.loads(request.data)
            body = {"content": [{"type": "text", "text": "  Sauberer Text.  "}]}
            return FakeResponse(json.dumps(body).encode())

        result = llm.polish("äh hallo", "sk-test", "formell", "de", opener=opener)
        self.assertEqual(result, "Sauberer Text.")
        self.assertEqual(seen["headers"]["x-api-key"], "sk-test")
        self.assertEqual(seen["body"]["model"], llm.MODEL)
        self.assertEqual(seen["body"]["messages"][0]["content"], "<diktat>äh hallo</diktat>")
        self.assertIn("formell", seen["body"]["system"])

    def test_network_error_returns_none(self):
        def opener(request, timeout):
            raise urllib.error.URLError("offline")

        self.assertIsNone(llm.polish("hallo", "sk-test", opener=opener))

    def test_invalid_json_returns_none(self):
        self.assertIsNone(llm.polish("hallo", "k", opener=lambda r, timeout: FakeResponse(b"nope")))


class PipelineTest(unittest.TestCase):
    def run_pipeline(self, mode, polisher=None, key="k", raw="äh hallo welt"):
        return pipeline.finalize(
            raw, "de", mode, "neutral", {"welt": "Welt"}, {}, key, polisher=polisher or (lambda *a: None)
        )

    def test_empty_text(self):
        self.assertEqual(self.run_pipeline("regeln", raw="   "), "")

    def test_rules_mode(self):
        self.assertEqual(self.run_pipeline("regeln"), "Hallo Welt")

    def test_off_mode_keeps_fillers_but_applies_dictionary(self):
        self.assertEqual(self.run_pipeline("aus"), "äh hallo Welt")

    def test_claude_mode_uses_polished_text(self):
        self.assertEqual(self.run_pipeline("claude", polisher=lambda *a: "Hallo welt."), "Hallo Welt.")

    def test_claude_mode_falls_back_to_rules(self):
        self.assertEqual(self.run_pipeline("claude", polisher=lambda *a: None), "Hallo Welt")

    def test_claude_mode_without_key_uses_rules(self):
        self.assertEqual(self.run_pipeline("claude", key=""), "Hallo Welt")


class PushToTalkTest(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.events = []
        self.talk = PushToTalk(
            lambda: self.events.append("start"),
            lambda: self.events.append("stop"),
            tap_seconds=0.3,
            clock=lambda: self.now,
        )

    def test_hold_to_talk(self):
        self.talk.press()
        self.now = 2.0
        self.talk.release()
        self.assertEqual(self.events, ["start", "stop"])

    def test_tap_starts_handsfree_until_next_press(self):
        self.talk.press()
        self.now = 0.1
        self.talk.release()
        self.assertEqual(self.events, ["start"])
        self.now = 5.0
        self.talk.press()
        self.talk.release()
        self.assertEqual(self.events, ["start", "stop"])
        self.assertEqual(self.talk.state, "idle")

    def test_key_repeat_is_ignored(self):
        self.talk.press()
        self.talk.press()
        self.talk.press()
        self.assertEqual(self.events, ["start"])


class KeyBindingTest(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.talk = PushToTalk(
            lambda: self.events.append("start"), lambda: self.events.append("stop"), tap_seconds=0.3, clock=lambda: 10.0
        )
        self.binding = KeyBinding(self.talk, "alt_r")

    def hold(self, name):
        self.binding.press(name)
        self.binding.release(name)

    def test_only_the_chosen_key_records(self):
        self.binding.press("f6")
        self.binding.release("f6")
        self.assertEqual(self.events, [])
        self.binding.press("alt_r")
        self.assertEqual(self.events, ["start"])

    def test_chosen_key_can_be_changed_while_running(self):
        self.binding.set_key("f6")
        self.binding.press("alt_r")
        self.assertEqual(self.events, [])
        self.binding.press("f6")
        self.assertEqual(self.events, ["start"])

    def test_changing_the_key_stops_a_running_recording(self):
        self.binding.press("alt_r")
        self.binding.set_key("f6")
        self.assertEqual(self.events, ["start", "stop"])
        self.assertEqual(self.talk.state, "idle")

    def test_next_key_press_is_captured_instead_of_recording(self):
        captured = []
        self.binding.capture_next(captured.append)
        self.assertTrue(self.binding.capturing)
        self.binding.press("f8")
        self.assertEqual(captured, ["f8"])
        self.assertFalse(self.binding.capturing)
        self.assertEqual(self.events, [])
        self.assertEqual(self.binding.key, "alt_r")  # erst die App übernimmt die Taste

    def test_capturing_the_chosen_key_itself_does_not_start_recording(self):
        captured = []
        self.binding.capture_next(captured.append)
        self.binding.press("alt_r")
        self.assertEqual((captured, self.events), (["alt_r"], []))

    def test_keys_without_name_are_reported_as_none_while_capturing(self):
        captured = []
        self.binding.capture_next(captured.append)
        self.binding.press(None)
        self.assertEqual(captured, [None])

    def test_capture_can_be_cancelled(self):
        self.binding.capture_next(lambda name: None)
        self.assertTrue(self.binding.cancel_capture())
        self.assertFalse(self.binding.cancel_capture())

    def test_keys_without_name_never_record(self):
        self.binding.press(None)
        self.binding.release(None)
        self.assertEqual(self.events, [])

    def test_old_left_key_names_are_converted(self):
        self.assertEqual(normalise_key_name("alt_l"), "alt")
        binding = KeyBinding(self.talk, "alt_l")
        binding.press("alt")
        self.assertEqual(self.events, ["start"])

    def test_unsuitable_and_suitable_keys(self):
        for name in ("enter", "space", "esc", "backspace", "up", "caps_lock", "", None):
            self.assertFalse(is_suitable_key(name), name)
        for name in ("alt_r", "alt_l", "cmd_r", "f6", "shift_r", "ctrl_r"):
            self.assertTrue(is_suitable_key(name), name)

    def test_display_names(self):
        self.assertEqual(display_name("alt_r"), "Rechte Option")
        self.assertEqual(display_name("alt_l"), "Linke Option")
        self.assertEqual(display_name("f6"), "F6")
        self.assertEqual(display_name("media_play_pause"), "MEDIA PLAY PAUSE")

    def test_key_name_reads_pynput_style_objects(self):
        class Special:
            name = "alt_r"

        self.assertEqual(key_name(Special()), "alt_r")
        self.assertIsNone(key_name(object()))


class ReviewFixesTest(unittest.TestCase):
    """Regressionstests für Fehler aus der Code-Prüfung."""

    def test_pasting_with_cmd_does_not_start_a_recording(self):
        events = []
        now = {"t": 0.0}
        talk = PushToTalk(lambda: events.append("start"), lambda: events.append("stop"), clock=lambda: now["t"])
        binding = KeyBinding(talk, "cmd", clock=lambda: now["t"])
        binding.mute(0.5)
        binding.press("cmd")  # das von der App selbst gedrückte Cmd+V
        binding.release("cmd")
        self.assertEqual(events, [])
        now["t"] = 0.6
        binding.press("cmd")
        self.assertEqual(events, ["start"])

    def test_stale_timeout_does_not_cancel_a_newer_capture(self):
        binding = KeyBinding(PushToTalk(lambda: None, lambda: None), "alt_r")
        first = binding.capture_next(lambda name: None)
        binding.press("esc")  # erste Erfassung verbraucht
        second = binding.capture_next(lambda name: None)
        self.assertFalse(binding.cancel_capture(first))  # alter Zeitablauf
        self.assertTrue(binding.capturing)
        self.assertTrue(binding.cancel_capture(second))

    def test_broken_key_values_do_not_crash(self):
        for value in (None, 7, "", []):
            self.assertEqual(display_name(value), "Keine")
            self.assertFalse(is_suitable_key(value))
            self.assertFalse(is_valid_key(value))
        self.assertEqual(normalise_key_name(None), "")

    def test_reset_after_refused_start_keeps_the_state_machine_in_sync(self):
        events = []
        talk = PushToTalk(lambda: events.append("start"), lambda: events.append("stop"), clock=lambda: 0.0)
        talk.press()
        talk.release()  # kurzer Tipp: Freihand, aber die App hat den Start abgelehnt
        talk.reset()
        self.assertEqual(talk.state, "idle")
        talk.press()
        self.assertEqual(events, ["start", "start"])


class LlmRobustnessTest(unittest.TestCase):
    def test_unexpected_response_shapes_return_none(self):
        for body in (b"[]", b'{"content": "text"}', b'{"content": [1, 2]}', b'{"content": [{"type": "text"}]}'):
            self.assertIsNone(llm.polish("hallo", "k", opener=lambda r, timeout, b=body: FakeResponse(b)), body)

    def test_language_is_named_in_the_prompt(self):
        self.assertIn("Englisch", llm.build_request("hi", "neutral", "en")["system"])
        self.assertNotIn("Englisch", llm.build_request("hi", "neutral", "auto")["system"])


class StorageTest(unittest.TestCase):
    def test_settings_roundtrip_and_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            settings = Settings(path)
            self.assertEqual(settings["model"], "small")
            settings["language"] = "en"
            settings["dictionary"] = {"x": "y"}
            again = Settings(path)
            self.assertEqual(again["language"], "en")
            self.assertEqual(again.dictionary_words(), ["y"])
            self.assertEqual(again["cleanup"], "regeln")

    def test_broken_settings_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(Settings(path)["model"], "small")

    def test_api_key_file_is_private(self):
        with tempfile.TemporaryDirectory() as folder:
            old = os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                self.assertEqual(load_api_key(folder), "")
                save_api_key("  sk-abc \n", folder)
                self.assertEqual(load_api_key(folder), "sk-abc")
                mode = (Path(folder) / "api_key.txt").stat().st_mode & 0o777
                self.assertEqual(mode, 0o600)
            finally:
                if old is not None:
                    os.environ["ANTHROPIC_API_KEY"] = old

    def test_history_keeps_newest_first_and_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            history = History(path, limit=3)
            for word in ("eins", "zwei", "drei", "vier"):
                history.add(word)
            self.assertEqual([e["text"] for e in history.recent()], ["vier", "drei", "zwei"])
            self.assertEqual([e["text"] for e in History(path).recent()], ["vier", "drei", "zwei"])


class SingleInstanceTest(unittest.TestCase):
    def test_second_instance_is_refused_until_the_first_ends(self):
        with tempfile.TemporaryDirectory() as folder:
            first = SingleInstance("demo", folder)
            second = SingleInstance("demo", folder)
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first._handle.close()  # Das Ende des Prozesses gibt die Sperre frei
            self.assertTrue(SingleInstance("demo", folder).acquire())

    def test_different_names_do_not_block_each_other(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(SingleInstance("eins", folder).acquire())
            self.assertTrue(SingleInstance("zwei", folder).acquire())


class StartupSafetyTest(unittest.TestCase):
    """Regressionstest: die gepackte App startete sich auf dem Mac endlos selbst neu."""

    def source(self, name):
        return (Path(__file__).resolve().parent.parent / name).read_text(encoding="utf-8")

    def test_freeze_support_runs_before_main(self):
        entry = self.source("app.py").split('if __name__ == "__main__":')[1]
        self.assertLess(entry.index("multiprocessing.freeze_support()"), entry.index("main()"))

    def test_single_instance_check_comes_before_the_window_is_created(self):
        main = self.source("app.py").split("def main():")[1]
        self.assertLess(main.index("instance.acquire()"), main.index("QApplication("))

    def test_model_download_does_not_create_process_locks(self):
        self.assertIn("tqdm.set_lock(threading.RLock())", self.source("engine.py"))


class VersionTest(unittest.TestCase):
    def test_version_file_is_a_version_number(self):
        version = (Path(__file__).resolve().parent.parent.parent / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_app_version_is_never_empty(self):
        self.assertTrue(app_version())


if __name__ == "__main__":
    unittest.main()
