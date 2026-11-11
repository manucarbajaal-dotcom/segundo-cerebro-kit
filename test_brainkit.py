"""Pruebas con datos sintéticos; no leen el cerebro privado."""
import contextlib
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import brainkit


class BrainKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_note_creation_never_overwrites(self):
        a = brainkit.create_note(self.root, "Revisión", "A", "demo")
        b = brainkit.create_note(self.root, "Revisión", "A", "demo")
        self.assertNotEqual(a, b)
        self.assertEqual(brainkit.issues(self.root), [])

    def test_topic_is_accent_insensitive(self):
        brainkit.create_note(self.root, "Revisión del índice", "A", "memoria")
        self.assertEqual(len(brainkit.notes(self.root, "REVISION indice")), 1)

    def test_closed_without_resolution_remains_pending(self):
        self.write("notes/a.md", "# A\nState: incorporated\n\n## Verified\nX")
        self.assertEqual(len(brainkit.notes(self.root, pending=True)), 1)
        self.assertIn("missing-resolution", [i["kind"] for i in brainkit.issues(self.root)])

    def test_body_cannot_close_note(self):
        self.write("notes/a.md", "# A\nState: pending\n\n## Verified\nState: incorporated\nResolution: example")
        self.assertEqual(brainkit.notes(self.root)[0].state, "pending")

    def test_closed_note_with_resolution_is_excluded(self):
        self.write("notes/a.md", "# A\nState: incorporated\nResolution: wiki/a.md\n\n## Verified\nX")
        self.assertEqual(brainkit.notes(self.root, pending=True), [])

    def test_links_alias_heading_and_code(self):
        self.write("wiki/alpha.md", "# Alpha")
        self.write("wiki/index.md", "[[alpha#Details|read]]\n```md\n[[missing]]\n```\n`[[inline]]`\n")
        self.assertEqual(brainkit.issues(self.root), [])

    def test_missing_link_reports_correct_line(self):
        self.write("wiki/index.md", "# Index\n\n[[missing]]")
        self.assertEqual(brainkit.issues(self.root)[0]["line"], 3)

    def test_ambiguous_basename_is_not_silently_resolved(self):
        self.write("one/page.md", "# One")
        self.write("two/page.md", "# Two")
        self.write("wiki/index.md", "[[page]]")
        self.assertEqual(brainkit.issues(self.root)[0]["kind"], "ambiguous-link")

    def test_hidden_directories_are_excluded(self):
        self.write(".git/secret.md", "[[missing]]")
        self.assertEqual(brainkit.markdown_files(self.root), [])

    def test_path_escape_is_broken(self):
        self.write("wiki/index.md", "[[../../outside]]")
        self.assertEqual(brainkit.issues(self.root)[0]["kind"], "broken-link")

    def test_context_budget_and_omission_notice(self):
        p = brainkit.create_note(self.root, "Big", "A", "demo")
        p.write_text(p.read_text(encoding="utf-8") + "X" * 2000, encoding="utf-8")
        result = brainkit.context(self.root, "", 8, 512)
        self.assertLessEqual(len(result), 512)
        self.assertIn("Included: 0", result)
        self.assertIn("Matching pending notes: 1", result)

    def test_check_exit_code(self):
        self.write("wiki/index.md", "[[missing]]")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brainkit.main(["--root", str(self.root), "check"]), 1)

    def test_header_injection_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            brainkit.main(["--root", str(self.root), "note", "X\nState: incorporated", "--author", "A"])
        self.assertFalse((self.root / "notes").exists())

    def test_bom_is_supported(self):
        self.write("notes/a.md", "\ufeff# BOM\nState: pending\n")
        self.assertEqual(brainkit.notes(self.root)[0].title, "BOM")

    def test_empty_resolution_does_not_consume_next_header_line(self):
        self.write("notes/a.md", "# A\nState: incorporated\nResolution:\nAuthor: A\n\n## Verified\nX")
        self.assertEqual(brainkit.notes(self.root)[0].resolution, "")
        self.assertEqual(len(brainkit.notes(self.root, pending=True)), 1)

    def test_symlink_notes_directory_is_rejected(self):
        target = self.root / "outside"
        target.mkdir()
        try:
            (self.root / "notes").symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("El sistema no permite crear symlinks")
        with self.assertRaises(ValueError):
            brainkit.notes(self.root)


    def export(self, files):
        allowlist = self.write("approved.json", json.dumps(files))
        out = self.root.parent / (self.root.name + "-release.zip")
        self.addCleanup(lambda: out.unlink(missing_ok=True))
        return out, brainkit.release(self.root, allowlist, out)

    def test_release_only_includes_allowlist_and_valid_hashes(self):
        self.write("README.md", "Public")
        self.write("private.md", "Do not publish")
        out, manifest = self.export(["README.md"])
        with zipfile.ZipFile(out) as archive:
            self.assertEqual(set(archive.namelist()), {"README.md", "RELEASE-MANIFEST.json"})
            self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(archive.read("README.md")).hexdigest())

    def test_release_blocks_email_without_echoing_value(self):
        value = "private" + "@" + "sample.invalid"
        self.write("README.md", value)
        with self.assertRaises(ValueError) as caught:
            self.export(["README.md"])
        self.assertIn("email-address", str(caught.exception))
        self.assertNotIn(value, str(caught.exception))

    def test_release_blocks_api_key(self):
        self.write("key.txt", "sk" + "-" + "A" * 40)
        with self.assertRaises(ValueError):
            self.export(["key.txt"])

    def test_release_rejects_escape_and_hidden_file(self):
        for name in ("../outside.md", ".env", "C:/private.md"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.export([name])

    def test_release_does_not_overwrite_destination(self):
        self.write("README.md", "Public")
        out, _ = self.export(["README.md"])
        before = out.read_bytes()
        with self.assertRaises(ValueError):
            brainkit.release(self.root, self.root / "approved.json", out)
        self.assertEqual(out.read_bytes(), before)

    def test_release_is_deterministic(self):
        self.write("README.md", "Public")
        first, _ = self.export(["README.md"])
        second = first.with_suffix(".other.zip")
        self.addCleanup(lambda: second.unlink(missing_ok=True))
        brainkit.release(self.root, self.root / "approved.json", second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_release_rejects_symlink_file(self):
        target = self.write("real.md", "Public")
        try:
            (self.root / "alias.md").symlink_to(target)
        except OSError:
            self.skipTest("El sistema no permite crear symlinks")
        with self.assertRaises(ValueError):
            self.export(["alias.md"])


if __name__ == "__main__":
    unittest.main()
