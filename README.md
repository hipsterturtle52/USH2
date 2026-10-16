# CLEP US History II study guide

A single self-contained HTML study guide for the **CLEP History of the United States II: 1865 to the Present** exam. Open `clep-us-history-ii-study-guide.html` in any browser. It works offline and needs no install or build step.

## What's inside

- **10 units** following the official 30% (1865–1914) / 70% (1915–present) split. Each unit has a lesson with cause → event → consequence chains, a must-know box, a timeline, a quiz, and flashcards.
- **393 original questions**, split into four pools that never overlap:
  - unit quizzes (10–15 per unit)
  - a 30-question diagnostic
  - two full-length 120-question practice exams with a 90-minute timer that can't be paused
- **Theme weights** match the official 30/30/10/20/10 split (political, social, economic, cultural, diplomatic).
- **267 flashcards** with Leitner spaced repetition, plus a mistake log you can drill.
- **Tools:** progress tracker, readiness meter, study-plan generator, one-page printable cheat sheet, dark mode, and keyboard shortcuts.
- **Saving:** progress is stored in your browser, and you can export or import it as JSON.

Exam facts and weights are in `outline.json`, with sources. Anything not confirmed on the College Board page is marked "unverified" in the app.

## Editing

The content lives in `src/units/u1.txt` … `u10.txt`, the cheat sheet in `src/cheatsheet.html`, and the app shell in `src/template.html`. After editing, rebuild and re-check:

```sh
python3 build.py              # writes clep-us-history-ii-study-guide.html and validates every question
python3 tests/audit.py        # structure, pools, weights, difficulty, answer positions, coverage
node tests/run_exam.js        # end-to-end UI run (needs Playwright + Chromium)
```

Question IDs follow their order in the unit files. Reordering or inserting questions can make saved browser progress point to the wrong questions.
