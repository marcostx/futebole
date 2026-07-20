# Results

The tables below summarize 20 seeded all-AI matches per configuration. Values
are mean ± sample standard deviation.

## Baseline

The evaluated baseline produces:

- **7.05 ± 2.58 goals**;
- **14.9 ± 2.5 shots**;
- **62.4 ± 6.6 passes**;
- **98.1% ± 1.6 pp pass completion**;
- **3.9 ± 2.7 pp possession deviation** from an even held-ball split; and
- **23.4 ± 4.1 turnovers** per 90-second match.

The ball is essentially still on only 0.8% of updates. Geometric player
overlap occurs on 1.6% of updates under the 20 px criterion; no pair crossed
the older, severe 15 px threshold in the evaluated baseline. The pre-rebuild
prototype measured 47.6% stillness and 98.4% severe overlap.

## Match production

| Configuration | Goals | Shots | Passes | Pass completion | Possession deviation | Turnovers |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 7.05 ± 2.58 | 14.9 ± 2.5 | 62.4 ± 6.6 | 98.1 ± 1.6% | 3.9 ± 2.7 pp | 23.4 ± 4.1 |
| tackle 0.01 | 8.05 ± 2.19 | 16.3 ± 1.7 | 58.3 ± 7.0 | 98.3 ± 1.6% | 3.4 ± 2.3 pp | 17.9 ± 2.0 |
| tackle 0.15 | 6.70 ± 1.72 | 15.2 ± 1.6 | 66.3 ± 7.9 | 98.2 ± 1.1% | 2.5 ± 2.0 pp | 37.1 ± 6.3 |
| pressure pass 0.01 | 6.30 ± 1.87 | 15.1 ± 1.8 | 40.2 ± 4.5 | 97.6 ± 2.9% | 2.8 ± 2.1 pp | 23.6 ± 3.5 |
| pressure pass 0.20 | 4.15 ± 1.39 | 13.9 ± 1.4 | 77.4 ± 7.6 | 98.1 ± 1.4% | 3.3 ± 2.1 pp | 21.9 ± 2.8 |
| long shots off | 0.85 ± 0.67 | 0.8 ± 0.7 | 68.1 ± 12.8 | 92.4 ± 4.1% | 3.8 ± 2.4 pp | 29.8 ± 6.0 |
| long-shot probability 0.10 | 6.90 ± 2.53 | 19.8 ± 1.2 | 64.8 ± 5.9 | 99.0 ± 1.1% | 2.2 ± 1.6 pp | 23.9 ± 3.2 |
| shooting range 100 px | 6.80 ± 2.14 | 15.4 ± 1.4 | 61.1 ± 6.5 | 98.3 ± 1.4% | 3.1 ± 2.2 pp | 21.6 ± 2.6 |
| shooting range 220 px | 8.75 ± 2.86 | 16.6 ± 1.9 | 59.2 ± 7.3 | 98.4 ± 1.6% | 2.8 ± 2.6 pp | 22.4 ± 3.0 |
| shape slide 0.2 | 6.80 ± 1.44 | 16.9 ± 1.1 | 56.6 ± 6.7 | 98.7 ± 2.1% | 3.6 ± 3.1 pp | 23.4 ± 3.5 |
| shape slide 0.8 | 4.05 ± 1.82 | 14.4 ± 2.5 | 71.0 ± 7.7 | 97.3 ± 1.6% | 2.1 ± 1.7 pp | 24.7 ± 3.9 |

## Ball flow and spatial structure

| Configuration | Free ball | Restarts | Moving speed | Still | Spread | Overlap |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 43.4 ± 2.7% | 1.1 ± 0.9 | 134 ± 6 px/s | 0.8 ± 0.5% | 183 ± 6 px | 1.6 ± 1.3% |
| tackle 0.01 | 43.8 ± 2.9% | 1.1 ± 0.9 | 137 ± 4 px/s | 0.8 ± 0.4% | 185 ± 5 px | 1.9 ± 1.7% |
| tackle 0.15 | 44.8 ± 3.4% | 0.8 ± 1.0 | 136 ± 4 px/s | 0.7 ± 0.5% | 186 ± 6 px | 1.3 ± 0.9% |
| pressure pass 0.01 | 32.9 ± 3.8% | 0.8 ± 0.6 | 123 ± 5 px/s | 0.4 ± 0.3% | 192 ± 10 px | 2.0 ± 1.1% |
| pressure pass 0.20 | 48.2 ± 3.0% | 0.9 ± 0.9 | 136 ± 4 px/s | 0.7 ± 0.5% | 184 ± 6 px | 1.3 ± 0.8% |
| long shots off | 24.2 ± 4.1% | 0.1 ± 0.2 | 99 ± 5 px/s | 0.0% | 198 ± 10 px | 12.2 ± 4.1% |
| long-shot probability 0.10 | 50.6 ± 1.5% | 1.2 ± 1.2 | 146 ± 4 px/s | 0.8 ± 0.5% | 189 ± 5 px | 0.3 ± 0.3% |
| shooting range 100 px | 44.0 ± 2.9% | 1.4 ± 1.2 | 136 ± 6 px/s | 0.8 ± 0.5% | 185 ± 5 px | 1.6 ± 1.1% |
| shooting range 220 px | 44.6 ± 3.1% | 0.3 ± 0.7 | 136 ± 6 px/s | 0.5 ± 0.4% | 184 ± 5 px | 1.0 ± 0.9% |
| shape slide 0.2 | 45.7 ± 2.2% | 1.2 ± 1.1 | 146 ± 5 px/s | 0.6 ± 0.3% | 198 ± 4 px | 0.9 ± 1.1% |
| shape slide 0.8 | 42.8 ± 2.8% | 0.6 ± 0.9 | 128 ± 5 px/s | 0.3 ± 0.5% | 179 ± 5 px | 1.8 ± 1.3% |

The free-ball share includes every pass and shot's 0.3-second in-flight
window, plus dead balls and contested loose balls. It should not be
interpreted as inactivity.

## Paired effects against baseline

Each cell is mean paired change with its two-sided sign-flip p-value.

| Configuration | Goals | Shots | Passes | Turnovers | Free ball | Spread |
|---|---:|---:|---:|---:|---:|---:|
| tackle 0.01 | +1.0 (0.148) | +1.4 (0.032) | -4.1 (0.043) | **-5.5 (<0.001)** | +0.4 (0.552) | +1.1 (0.371) |
| tackle 0.15 | -0.3 (0.612) | +0.3 (0.707) | +3.9 (0.060) | **+13.8 (<0.001)** | +1.5 (0.119) | +2.1 (0.308) |
| pressure pass 0.01 | -0.8 (0.404) | +0.1 (0.873) | **-22.2 (<0.001)** | +0.1 (0.929) | **-10.5 (<0.001)** | **+8.8 (0.002)** |
| pressure pass 0.20 | **-2.9 (<0.001)** | -1.0 (0.127) | **+15.0 (<0.001)** | -1.4 (0.246) | **+4.9 (<0.001)** | +0.2 (0.920) |
| long shots off | **-6.2 (<0.001)** | **-14.1 (<0.001)** | +5.7 (0.051) | **+6.3 (<0.001)** | **-19.2 (<0.001)** | **+14.8 (<0.001)** |
| long-shot probability 0.10 | -0.1 (0.900) | **+4.8 (<0.001)** | +2.4 (0.253) | +0.5 (0.765) | **+7.2 (<0.001)** | **+5.7 (0.002)** |
| shooting range 100 px | -0.2 (0.747) | +0.5 (0.431) | -1.3 (0.542) | -1.8 (0.060) | +0.6 (0.352) | +1.8 (0.268) |
| shooting range 220 px | **+1.7 (0.009)** | **+1.7 (0.002)** | -3.2 (0.082) | -1.1 (0.303) | +1.2 (0.030) | +0.3 (0.881) |
| shape slide 0.2 | -0.2 (0.770) | +2.0 (0.012) | -5.8 (0.019) | +0.1 (1.000) | **+2.3 (0.010)** | **+14.3 (<0.001)** |
| shape slide 0.8 | **-3.0 (0.001)** | -0.6 (0.507) | **+8.6 (<0.001)** | +1.3 (0.388) | -0.6 (0.474) | -4.2 (0.083) |

Bold cells have unrounded \\(p<0.01\\); displayed values are rounded.

## Tackle probability controls volatility

Turnovers move monotonically from 17.9 at tackle probability 0.01, through
23.4 at baseline, to 37.1 at 0.15. Goal production remains within noise.

The contest layer therefore changes *who* holds the ball without destabilizing
the shooting and scoring chain. At low tackle probability, carriers survive
longer, shoot slightly more, and make fewer recycling passes.

## Eager pressure offloading hurts penetration

Pressure-pass probability produces the largest circulation swing:

- 0.01: 40.2 passes and 32.9% free-ball share;
- baseline 0.06: 62.4 passes and 43.4% free-ball share;
- 0.20: 77.4 passes and 48.2% free-ball share.

At 0.20, goals fall by 2.9 per match. Pressured carriers release the ball
before dribbling into the long-shot band; backward outlets increase
circulation without creating penetration.

## Long shots are load-bearing

Disabling probabilistic shots from 150–320 px reduces:

- shots from 14.9 to 0.8; and
- goals from 7.05 to 0.85.

The block, goal-side marking, and rest defence make clean entry into the
inner shooting zone rare. Long shots are the release valve that prevents
sterile possession. The ball still moves continuously with long shots
disabled—stillness falls to 0%—but play becomes lower-speed midfield
circulation, with fewer in-flight frames and a wider team shape.

Increasing long-shot probability from 0.02 to 0.10 adds 4.8 shots but no goals.
Distance-scaled noise and the goalkeeper absorb the extra low-quality attempts.

## Shooting range is asymmetric

Reducing deterministic shooting range from 150 to 100 px changes little
because the inner zone is rarely reached.

Extending it to 220 px increases goals by 1.7 and shots by 1.7. The larger
range converts part of the probabilistic long-shot band into guaranteed
attempts. Opportunity creation, rather than finishing power, is the main
offensive bottleneck.

## Excess formation elasticity creates congestion

A rigid slide gain of 0.2 keeps the widest shape (198 px spread) and slightly
increases shots without changing goals.

A high gain of 0.8 pulls the formation toward the ball:

- spread shrinks;
- passes rise by 8.6; and
- goals fall by 3.0.

Nearby marked teammates create short circulation and occupy the carrier's
dribbling corridors. The result is emergent congestion, not an explicit rule.

## Runtime

One 90-second match with 5,625 updates and 12 agents took
0.760 ± 0.011 seconds on the measured Apple laptop-class CPU, approximately
118× real time and 7,397 updates/s including instrumentation.

The complete 220-match sweep ran in under three minutes, making the protocol
practical as a regression and tuning harness.
