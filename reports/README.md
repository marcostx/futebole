# Reports

This folder tracks the **evolution of the soccer simulation** over time. Each
report captures the state of the game at a point in time: how a match actually
plays out, measured metrics, observed problems, and a prioritized list of
improvements.

Use these reports to:
- Compare behavior between versions (did possession balance out? are goals being scored?).
- Verify that fixes had the intended effect.
- Decide what to work on next.

## How to generate a report

Matches are observed headlessly with the instrumented runner at the repo root:

```bash
source venv/bin/activate
python monitor_match.py
```

It runs a full match on a virtual clock (completes instantly), prints match
statistics, and saves screenshots to `match_frames/`. Copy the relevant
screenshots into `reports/assets/<report-id>/` and summarize the run in a new
report file.

## Naming convention

```
reports/<YYYY-MM-DD>-v<version>-<label>.md
reports/assets/<YYYY-MM-DD>-v<version>/
```

## Report index

| Date | Version | Report | Headline result |
|------|---------|--------|-----------------|
| 2026-07-09 | 0.1.0 | [Baseline](./2026-07-09-v0.1.0-baseline.md) | 0–0, players clump in a corner; ball never really moves |
