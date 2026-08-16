# Shot Diet

### Separating shot selection from shot making in the NBA — and finding out which one a team can actually coach

**AQX Sports Analytics Data Bowl 3.0**

Every field goal attempt is two decisions welded together: **what shot the offence
generated**, and **whether the player put it in**. Points per shot mixes them, so a
centre who only dunks looks like a great shooter and a guard manufacturing
late-clock jumpers looks like a bad one.

Shot Diet pulls **1,087,633 regular-season field goal attempts** across five seasons
(2021-22 → 2025-26), splits every player's efficiency into those two components,
measures how *knowable* each one is, and then tests whether the resulting advice
survives contact with the following season.

---

## The finding

| | Shot selection | Shot making |
|---|---|---|
| Attempts before the metric is 50% signal | **11** | **311** |
| Within-season reliability (split-half, Spearman-Brown) | **0.97** | **0.62** |
| Season-to-season correlation | **0.90** | **0.58** |
| Spread across players (SD, pts/100) | 8.5 | 8.8 |
| …of which is *repeatable* | **8.4** | 6.9 |

In a single season the two look equally decisive — they vary across players by
almost exactly the same amount. Strip out measurement noise and **59% of the
genuinely repeatable difference between players is simply which shots they take.**

They also pull against each other (**r = −0.27**): players handed the easiest shots
are the weaker shot-makers, and the best shot-makers are handed the hardest shots.
That is precisely why raw efficiency flatters the first group and buries the second.

> **2025-26:** DeMar DeRozan has the worst shot diet of any high-volume player in the
> league (**−17.1** pts/100) while being a clearly above-average shot-maker
> (**+12.0**). Rudy Gobert is the mirror image (**+35.5** selection, **−8.2** making).
> Nikola Jokić takes a *below-average* diet (−6.9) and is the league's second-best
> maker of it (+21.3).

### The part that surprised us

The project ships a prescriptive optimiser: a linear program that reallocates 5% of
a player's attempts across six zones to maximise expected points, using
empirical-Bayes estimates of his zone-by-zone shooting. Graded against the
**following** season, it is worth **+2.49 points per 100 shots** and helps 99.5% of
players.

Then we ran the controls that matter:

| Out-of-sample comparison | Mean pts/100 | 95% CI |
|---|---|---|
| Personalised prescription vs. do nothing | **+2.49** | +2.43 … +2.55 |
| **Generic league-average advice** vs. do nothing | **+2.50** | +2.44 … +2.56 |
| Personalised vs. generic league-average advice | **−0.01** | −0.04 … +0.03 |
| Shrunk vs. unshrunk (raw hot-zone) advice | **+0.33** | +0.26 … +0.40 |

**Personalising the shot diet to the individual shooter is worth nothing.** All of
the gain comes from the league-average zone structure — get out of the mid-range.
This is not an artefact of a tight constraint: the null holds from a 3% to a 20% move
budget, and the two prescriptions genuinely disagree for about half the league
(completely, for the top decile). Meanwhile *shrinking* rates clearly beats trusting
them, and the advantage grows the more volume you let the optimiser move.

It is the same story the reliability table tells. Shot making needs 311 attempts to
be half signal; a single zone within a single season never gets close.

### What a staff should do with this

- **Shot quality is a scheme problem, not a personnel problem.** Selection shows up
  in eleven attempts and persists at r = 0.90 across seasons. It is the high-leverage,
  low-variance lever.
- **Coach the diet with league-average zone values.** Do not build a personalised
  shot-diet plan off one season of shooting splits — you will be coaching noise.
- **Stop paying for shot-making outliers as if they were fixed.** A third of the
  season-to-season variance in making does not carry over.
- **Read efficiency leaderboards through the split.** A 1.36 pts/shot centre and a
  1.04 pts/shot guard can be the same player wearing different roles.

---

## What's in here

| Page | What it does |
|---|---|
| **The finding** | The reliability result, the stabilisation curves, the quadrant chart, and the out-of-sample verdict |
| **Players** | Leaderboard and quadrant scatter, plus per-player hex shot charts, zone profiles and season histories |
| **Shot-diet optimiser** | Live LP — pick a player, set the move budget, get a coachable prescription |
| **Teams** | The same split across all thirty offences |
| **Method & validation** | Model metrics, calibration, the anti-fooling-ourselves guards, and an honest list of what the data cannot see |

---

## Method

For each attempt a gradient-boosted model estimates the probability a **league-average**
shooter converts it; times the shot's point value that gives expected points per shot
(**xPPS**). Over a player's season this splits exactly:

```
PPS − league PPS  =  (xPPS − league PPS)  +  (PPS − xPPS)
                          shot selection        shot making
```

**Features.** Shot geometry (x, y, distance, angle off-centre), clock state (period,
seconds remaining), venue, season, and the play type in `ACTION_TYPE`. Two models are
fit: `xPPS-loc` on geometry alone, and `xPPS-full` adding play type — used for the
headline split, on the reasoning that whether a shot is a cut, a pull-up or a
turnaround fadeaway is a property of the offence rather than the shooter's touch.

| Model | Log loss | Brier | AUC | Gain vs. base rate |
|---|---|---|---|---|
| League mean make rate | 0.6915 | 0.2492 | 0.500 | — |
| Zone average make rate | 0.6587 | 0.2330 | 0.633 | 4.74% |
| Distance spline logistic | 0.6542 | 0.2309 | 0.642 | 5.39% |
| xPPS-loc (geometry) | 0.6492 | 0.2289 | 0.648 | 6.12% |
| **xPPS-full (+ play type)** | **0.6358** | **0.2236** | **0.663** | **8.06%** |

Calibration matters more than discrimination here — an uncalibrated model would not
make the decomposition add up. Across all 1.09M shots, model expected points sit
**0.004 points per 100** from actual scoring.

### Guards against fooling ourselves

- **No player grades himself.** Every prediction used to evaluate a player is
  out-of-fold with folds grouped **by player ID** — the model scoring a player has
  never seen one of his shots. Without this a high-volume specialist partly sets his
  own benchmark.
- **The API silently truncates.** `shotchartdetail` caps every response at 102,400
  rows, so a whole-season request returns roughly the first half of the season with
  no error and no warning. The loader pages by calendar month and **asserts** no chunk
  reaches the cap. All five seasons come back at the full 1,230 games.
- **Clock management removed.** 3,696 backcourt attempts and buzzer heaves are
  dropped — they are not shot selection.
- **Zones kept coarse on purpose.** An earlier ten-zone scheme split left from right;
  the empirical-Bayes prior strength swung from k = 199 on one wing to k = 2018 on the
  other *for the same shot*. That is binomial noise, not a talent difference, and it
  made the optimiser prefer left-side threes to identical right-side threes. Six
  well-sampled zones instead.
- **Rates are shrunk, not trusted.** Method-of-moments beta-binomial shrinkage, so
  only spread exceeding binomial noise is treated as talent.
- **The prescriptive tool is graded out of sample**, against two controls, with
  bootstrap CIs — which is how we found the null above rather than shipping a
  personalisation feature that does nothing.

### What this cannot see

- **No defender.** The public feed has no defender distance, so "selection" means
  location, play type and clock — not whether the shot was open. Some of what lands in
  *making* is really the ability to create separation.
- **Play type is a coarse, human-scored proxy.**
- **No free throws or fouls**, so foul-drawing diets are undervalued.
- **The optimiser assumes zone rates hold under reallocation.** They will not exactly
  — the marginal corner three is not the average one. The small default move budget is
  there to keep that assumption honest.
- **Selection is not free.** Telling a guard to take fewer pull-ups only works if
  someone else can generate the shot.

---

## Running it

Requires **Python 3.10 or newer**. Two commands:

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

That's it — the dashboard opens at `http://localhost:8501`. Every processed table is
committed, so **nothing is downloaded and no model is fitted at startup.** The app
never contacts stats.nba.com at runtime.

<details>
<summary>Windows, step by step</summary>

```powershell
git clone https://github.com/s155003/shot-diet.git
cd shot-diet
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```
</details>

### Reproducing the analysis from scratch

Only needed to rebuild the data or extend it — not to run the dashboard.

```bash
python src/fetch.py          # ~4 min, pulls 1.09M shots from stats.nba.com
python src/run_pipeline.py   # ~2.5 min, fits the models and rebuilds every table
```

`fetch.py` writes to `data/raw/` (gitignored, ~30 MB) and skips seasons it already
has. `run_pipeline.py` overwrites `data/processed/` and `reports/summary.json`.

### Verifying it

```bash
pip install -r requirements-dev.txt
python -m pytest tests/          # renders all five dashboard pages headlessly
python src/sensitivity.py        # robustness checks on the headline null
```

`tests/shoot.py` also screenshots each page, which needs
`python -m playwright install chromium` first.

### Hosting a live link

Because the processed tables ship in the repo, this deploys to
[Streamlit Community Cloud](https://share.streamlit.io) with no build step: point it
at this repo with `app/streamlit_app.py` as the entry point and Python 3.10+.

### Layout

```
src/fetch.py          paged pull from stats.nba.com, with the row-cap assertion
src/features.py       shot events -> modelling table, zones, exclusions
src/model.py          xPPS models, player-grouped OOF predictions, baselines
src/analyze.py        decomposition, empirical Bayes, reliability, the LP, backtest
src/run_pipeline.py   runs all of it, writes data/processed/ and reports/summary.json
src/sensitivity.py    robustness checks on the headline null
app/                  Streamlit dashboard (theme, court geometry, charts, pages)
tests/                headless render tests for every page
```

## Data

Public `stats.nba.com` `shotchartdetail` endpoint via
[`nba_api`](https://github.com/swar/nba_api). 1,087,633 regular-season field goal
attempts, 2021-22 through 2025-26, 1,230 games per season. 2019-20 and 2020-21 are
excluded deliberately: the bubble and the 72-game season distort both shot selection
and rest patterns enough to contaminate year-over-year stability estimates.

## Licence

MIT.
