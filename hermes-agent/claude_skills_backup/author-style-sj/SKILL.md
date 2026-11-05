---
name: author-style-sj
description: Write in the voice of Seal Josephson (Fodor-Josephson Szilárd) for the hc / Happiness Consulting project. Use whenever drafting, rewriting, translating, or reviewing a book chapter, article, lead, page text, or exercise for the hc project or the book "Szakmai intuíció a vezetői döntéshozásban — Csípőből Tüzelünk" (HU or EN). Not for UI strings, code, or commit messages.
---

# Seal Josephson author style

The full analysis is the source of truth. Do not write from memory of this file alone.

## Workflow (every time)

1. Read the guide: `D:\Projects\super_code\docs\author-style\seal-josephson-szerzoi-stilus.md`
   (hc copy: `D:\Projects\hc\docs\style\szerzoi-stilus.md`; if the two differ, the hc copy is newer).
   - Section **D** (18 Do/Avoid rules + EN notes) is mandatory.
   - Section **A8** (terminology) is mandatory for any text that uses the method's terms.
   - Read A (voice) and B (what the author changed in AI drafts) when writing a whole chapter.
2. Check terms against `D:\Projects\hc\content\glossary.json` (canonical). SDx colours: BÉZS, LILA, PIROS, KÉK, NARANCS, ZÖLD, SÁRGA, TÜRKÍZ, KORALL, KÉKESZÖLD, ARANY, LIME (EN: CORAL, TEAL, GOLD, LIME). All caps; mixed levels like "KÉK-Piros".
3. Write the draft.
4. Run the self-check below before handing it over.

## Self-check (fast pass over the draft)

- Opens with 2-3 short questions or a scene; content starts by paragraph 2.
- "Mi" in body text, tegező imperative in exercises, first person for the author's own anecdotes.
- Every abstract claim has an everyday image (image first, evidence second).
- Paragraphs 1-5 sentences; short subheads, often questions.
- No chapter map / signposting ("Ebben a fejezetben...", "Mint az előző fejezetben láttuk").
- No "nem X, hanem Y" aphorism closers, no dramatic set-ups ("És itt jön a legszebb rész").
- Exclamation marks about 2-4 per 10 000 chars; dashes at most about 1 per 1000 chars; `(!)` at most once.
- Sources named (researcher, institution, year, n).
- Ends with a doable exercise (numbered steps + duration) or a question to the reader.
- No machine-translation tells: "professzionális intuíció", "örömteli kilátás", "felelős boldogság", "Ön"-forma, English colour names in HU text.
- **No invented anecdote, number, or quote in the author's name**, and no sharp religious/political verdict unless the author supplied it.

## Kill switch

Delete `~/.claude/skills/author-style-sj/`. The guide document has no side effects.
