#!/usr/bin/env python3
"""Smoketest for sync_codex_brain.py -- runs offline against a synthetic CLAUDE.md."""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sync_codex_brain as s

FAKE_CLAUDE_MD = """# CLAUDE.md

Intro prose that belongs to no section and must not be copied.

## Some unrelated Claude Code machinery

This section is NOT in SHARED_SECTION_PREFIXES and must be dropped.

## Working style

- Read relevant files before editing.

### A subsection that belongs to Working style

Must travel with its parent section.

## CONSTITUTIONAL RULES (S0 tier)

1. **Decision-gate on irreversible ops** -- ask before push.

## No decorative unicode in code or docs

Use ASCII equivalents.

## Statusline something Claude-only

Also must be dropped.
"""


def test_extract_only_shared_sections():
    found = s.extract_sections(FAKE_CLAUDE_MD)
    headings = [h for h, _ in found]
    assert any(h.startswith("Working style") for h in headings)
    assert any(h.startswith("CONSTITUTIONAL RULES") for h in headings)
    assert any(h.startswith("No decorative unicode") for h in headings)
    assert not any("machinery" in h for h in headings), "unlisted section leaked in"
    assert not any("Statusline" in h for h in headings), "unlisted section leaked in"
    assert len(found) == 3, f"expected exactly 3 shared sections, got {headings}"
    print("[ok] extract_sections: copies listed sections, drops everything else")


def test_subsections_travel_with_parent():
    body = dict(s.extract_sections(FAKE_CLAUDE_MD))["Working style"]
    assert "### A subsection that belongs to Working style" in body
    assert "Must travel with its parent section." in body
    # ...but the NEXT top-level section must not bleed in.
    assert "CONSTITUTIONAL" not in body
    print("[ok] extract_sections: subsections travel with parent, siblings do not")


def test_intro_prose_not_copied():
    joined = "\n".join(b for _, b in s.extract_sections(FAKE_CLAUDE_MD))
    assert "belongs to no section" not in joined
    print("[ok] extract_sections: pre-heading prose is not copied")


def test_empty_match_is_fatal_not_silent():
    """A renamed heading must fail loudly -- a silently empty brain is worse."""
    try:
        s.build_from_text("# CLAUDE.md\n\n## Nothing matches here\n\ntext\n",
                          Path("."), Path.home())
    except SystemExit as e:
        assert "no shared sections matched" in str(e)
        print("[ok] build: exits loudly when no section matches (no silent empty file)")
        return
    raise AssertionError("build must raise SystemExit when nothing matches")


def test_project_slug():
    assert s.project_slug(Path(r"D:\projects\super_claude")) == "D--projects-super-claude"
    assert s.project_slug(Path(r"D:\projects\super_code")) == "D--projects-super-code"
    print("[ok] project_slug: derives the Claude Code project directory name")


def test_cli_check_detects_drift():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "CLAUDE.md"
        src.write_text(FAKE_CLAUDE_MD, encoding="utf-8")
        out = Path(tmp) / "AGENTS.md"
        script = str(Path(__file__).parent / "sync_codex_brain.py")

        r = subprocess.run([sys.executable, script, "--check", "--source", str(src),
                            "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 1 and "STALE" in r.stdout, r.stdout + r.stderr

        r = subprocess.run([sys.executable, script, "--source", str(src),
                            "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 0 and out.is_file(), r.stdout + r.stderr

        r = subprocess.run([sys.executable, script, "--check", "--source", str(src),
                            "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 0 and "OK" in r.stdout, r.stdout + r.stderr

        out.write_text(out.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8")
        r = subprocess.run([sys.executable, script, "--check", "--source", str(src),
                            "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 1 and "STALE" in r.stdout, r.stdout + r.stderr
    print("[ok] --check: missing -> stale, generated -> ok, hand-edited -> stale")


def test_generated_file_warns_against_hand_editing():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "CLAUDE.md"
        src.write_text(FAKE_CLAUDE_MD, encoding="utf-8")
        text = s.build(src, Path(tmp), Path.home())
    assert "GENERATED FILE -- DO NOT EDIT BY HAND" in text
    assert "sync_codex_brain.py" in text
    assert "Kill switch" in text
    assert "Shared memory" in text
    assert "What Codex does NOT have" in text
    print("[ok] build: header warns, appendix documents memory + missing machinery")


def main():
    test_extract_only_shared_sections()
    test_subsections_travel_with_parent()
    test_intro_prose_not_copied()
    test_empty_match_is_fatal_not_silent()
    test_project_slug()
    test_generated_file_warns_against_hand_editing()
    test_cli_check_detects_drift()
    print("\n[ok] All smoketests passed!")


if __name__ == "__main__":
    main()
