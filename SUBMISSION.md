# Shot Diet: project description

*Prepared for the AQX Sports Analytics Data Bowl 3.0. Paste into the Devpost
description field; trim the closing sections if a shorter form is wanted.*

---

## Inspiration

Points per shot is the number everyone quotes, and it answers the wrong question.
Rudy Gobert scored **1.365** points a shot in 2025-26; Luka Dončić scored **1.127**.
Nobody thinks Gobert is the better shooter. He has a better *diet*, taking only the
shots the offence hands him at the rim, while Dončić manufactures contested jumpers.
Every attempt is two separate decisions welded together, and the box score refuses to
pull them apart.

So we asked a question a front office actually has to answer: **of the two, which one
can a team change?**

## What it does

Shot Diet pulls **1,087,633 regular-season field goal attempts** (2021-22 through
2025-26, every game of all five seasons) and splits each player's efficiency in two:

```
PPS − league PPS  =  (xPPS − league PPS)  +  (PPS − xPPS)
                          shot SELECTION       shot MAKING
```

A gradient-boosted model estimates what a *league-average* shooter would score on each
attempt given where it came from, how it was created, the clock and the venue. What
the diet is worth in average hands is **selection**. What the shooter added on top is
**making**. They sum exactly to efficiency above league average.

The dashboard then answers *how much you can trust each half*, and ships a
coach-facing optimiser that turns it into a prescription.

## The finding

| | Shot selection | Shot making |
|---|---|---|
| Attempts before the metric is 50% signal | **11** | **311** |
| Within-season reliability (split-half, Spearman-Brown) | **0.97** | **0.62** |
| Season-to-season correlation | **0.90** | **0.58** |
| Spread across players (SD, pts/100) | 8.5 | 8.8 |
| Of which is *repeatable* | **8.4** | 6.9 |

In any one season the two look equally decisive, varying across players by almost
exactly the same amount, which is why they get conflated. Strip out measurement noise
and **59% of the genuinely repeatable difference between players is simply which shots
they take.** Selection is knowable from eleven attempts. Shot making needs most of a
season before half of it is even signal.

The two also pull *against* each other (**r = −0.27**): the players handed the easiest
shots are the weaker shot-makers, and the best shot-makers are handed the hardest
shots. That is precisely why raw efficiency flatters one group and buries the other.

> **2025-26.** DeMar DeRozan has the worst shot diet of any high-volume player in the
> league (**−17.1** pts/100, with 48.5% of his attempts from the mid-range) while being
> a clearly above-average shot-maker (**+12.0**). Gobert is the exact mirror
> (**+35.5** / **−8.2**). Jokić takes a *below-average* diet and is the league's
> second-best maker of it (**+21.3**), for the fifth straight season.

## The result we did not expect

The optimiser is a linear program: reallocate at most 5% of a player's attempts across
six zones to maximise expected points, using empirical-Bayes estimates of his own
zone-by-zone shooting. Graded against the **following** season it is worth **+2.49
points per 100 shots** and helps 99.5% of players. A nice headline, so we ran the
controls that could kill it.

| Out-of-sample comparison | Mean pts/100 | 95% CI |
|---|---|---|
| Personalised prescription vs. do nothing | **+2.49** | +2.43 to +2.55 |
| **Generic league-average advice** vs. do nothing | **+2.50** | +2.44 to +2.56 |
| Personalised vs. generic league-average advice | **−0.01** | −0.04 to +0.03 |
| Shrunk vs. unshrunk (raw hot-zone) advice | **+0.33** | +0.26 to +0.40 |

**Personalising a shot diet to the individual shooter is worth nothing.** Every bit of
the gain comes from the league-average zone structure: get out of the mid-range.
This is not an artefact of a tight constraint, because the null holds from a 3% to a
20% move budget, and the two prescriptions genuinely disagree for about half the league
(completely, for the top decile). Meanwhile *shrinking* rates clearly beats trusting
them, and the advantage widens the more volume the optimiser is allowed to move.

It is the same story the reliability table tells. Shot making needs 311 attempts to be
half signal; a single zone inside a single season never gets close. We shipped the
negative result rather than the feature.

## Actionable impact

- **Shot quality belongs to the scheme far more than to the roster.** Selection shows
  up in eleven attempts and persists at r = 0.90. It is the high-leverage, low-variance
  lever a staff actually controls.
- **Coach the diet with league-average zone values.** Do not build a personalised
  shot-diet plan off one season of shooting splits; you will be coaching noise. This is
  a concrete warning about something analytics departments really do.
- **Stop paying for shot-making outliers as if they were fixed.** A third of the
  season-to-season variance in making does not carry over. The stabilisation thresholds
  say exactly how much of a hot season to believe.
- **Read every efficiency leaderboard through the split.** A 1.36 pts/shot centre and a
  1.13 pts/shot guard can be the same player wearing different roles.
- **Per-player prescriptions are in the tool**, sized to what a staff would install.
  DeRozan: move 50 attempts from the long mid-range to the rim, worth +26 points over a
  season.

## How we built it

Python: `nba_api` → pandas → scikit-learn → SciPy LP → Streamlit + Plotly.

`HistGradientBoostingClassifier` over shot geometry (x, y, distance, angle off-centre),
clock state, venue, season and the recorded play type. Two models: geometry-only and
geometry-plus-play-type; the latter drives the headline split, on the reasoning that
whether a shot is a cut, a pull-up or a turnaround fadeaway is a property of the
offence rather than the shooter's touch.

| Model | Log loss | Brier | AUC | Gain vs. base rate |
|---|---|---|---|---|
| League mean make rate | 0.6915 | 0.2492 | 0.500 | |
| Zone average make rate | 0.6587 | 0.2330 | 0.633 | 4.74% |
| Distance spline logistic | 0.6542 | 0.2309 | 0.642 | 5.39% |
| xPPS-loc (geometry) | 0.6492 | 0.2289 | 0.648 | 6.12% |
| **xPPS-full (+ play type)** | **0.6358** | **0.2236** | **0.663** | **8.06%** |

Calibration matters more than discrimination here, because an uncalibrated model would
not make the decomposition add up. Across all 1.09M shots the model's expected points sit
**0.004 points per 100** from actual scoring, and the worst of twenty probability bins
is off by 0.008.

## Challenges

**The API lies quietly.** `shotchartdetail` truncates every response at exactly 102,400
rows. Request a season and you get roughly the first half of it, through mid-January,
with no error and no warning. Our first pull looked perfectly healthy and was missing
53% of the data. The loader now pages by calendar month and *asserts* no chunk reaches
the cap; all five seasons come back at the full 1,230 games.

**Zones that were too clever.** An initial ten-zone scheme split left from right. The
empirical-Bayes prior strength then swung from k = 199 on one wing to k = 2018 on the
other *for the same shot*. That is binomial noise rather than talent, and the optimiser
started recommending left-side threes over identical right-side threes. Collapsed to
six well-sampled zones.

**Players grading themselves.** A high-volume specialist takes enough shots to shift
the very model that judges him. Every prediction used to evaluate a player is
out-of-fold with folds grouped **by player ID**, so the model scoring a player has
never seen one of his shots.

## What we learned

That the honest version of a result is usually the more interesting one. We set out to
build a personalised shot-diet recommender and finished with proof that personalisation
does not work at this sample size, which is a far more useful thing to hand a coaching
staff than a tool that quietly fits noise.

## What's next

Defender distance (the public feed has none, so some of what we call "making" is really
separation-creation), free throws and foul-drawing, lineup-level selection so the
"someone else has to generate that shot" constraint becomes explicit, and a possession
model so reallocation accounts for the defence adjusting.

---

**Live app:** https://shot-diet-eb5nmvww489spbby72agpr.streamlit.app/

**Repo:** https://github.com/s155003/shot-diet

**Run it** (Python 3.10+, two commands, nothing downloaded at startup):

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Every processed table is committed, so the dashboard runs without re-fetching and
never contacts stats.nba.com at runtime.
