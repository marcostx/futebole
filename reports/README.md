# Le Futebole Documentation

Le Futebole is a compact 2D soccer simulation with timestep-aware
physics, explicit possession and restart rules, role-aware team tactics, and
mixed human/AI control.

The documentation has two complementary parts:

- The [technical paper](paper/README.md) explains how the current simulation
  works, from the update loop and physics through tactical AI, human controls,
  and the seeded evaluation protocol.
- The development reports below preserve point-in-time observations of the
  game. They show how the simulation evolved and why particular mechanics were
  introduced.

## Development reports

Each report captures the state of the game at a point in time: how a match
actually plays out, measured metrics, observed problems, and a prioritized
list of improvements.

Use these reports to:
- Compare behavior between versions (did possession balance out? are goals being scored?).
- Verify that fixes had the intended effect.
- Decide what to work on next.

## How to generate a report

Matches are observed headlessly with the instrumented runner at the repo root:

```bash
source venv/bin/activate
python monitor_match.py --seed 7 \
  --output-dir reports/assets/2026-07-19-v0.2.0
```

It runs a full match on a virtual clock (completes instantly), prints match
statistics, and saves screenshots directly to the report asset directory.
Change the seed and output directory for each report. Without `--output-dir`,
screenshots are written to the ignored `match_frames/` scratch directory.

## Naming convention

```
reports/<YYYY-MM-DD>-v<version>-<label>.md
reports/assets/<YYYY-MM-DD>-v<version>/
```

## Report index

| Date | Version | Report | Headline result |
|------|---------|--------|-----------------|
| 2026-07-09 | 0.1.0 | [Baseline](./2026-07-09-v0.1.0-baseline.md) | 0–0, players clump in a corner; ball never really moves |
| 2026-07-19 | 0.2.0 | [Rebuild](./2026-07-19-v0.2.0-rebuild.md) | 2–1 seeded match; stable shape, active ball, rules, tactics, and mixed control |
