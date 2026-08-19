# Design brief

How this product is meant to look and behave. Written to be handed to someone
with no prior context, so it states the reasoning behind each rule rather than
just the rule. Where a rule exists because something was tried and failed, the
failure is recorded, because the failure is the argument.

---

## 1. What this product is

A reference tool for NBA shot data. It splits every player's scoring into two
components (the quality of shots he gets, and how well he makes them) and lets
someone look up any player, team or leaderboard.

**The mental model is Basketball Reference, not a dashboard and not an article.**
That single sentence resolves most design questions. When in doubt, ask what
Basketball Reference would do.

---

## 2. The five principles

These override any other instinct. They are ordered by how often they get
violated.

### 2.1 Nothing renders until it is asked for

The landing page must not display any specific player's data. No default player,
no "featured" player, no hero example. A first-time visitor sees a search box and
an empty state, and the page stays empty until they type a name and pick someone.

This is not a performance rule, it is a comprehension rule. Preloaded data
implies that data is the answer to a question the visitor did not ask.

**Enforcement:** there is an automated test asserting the landing page renders
zero tables and zero summary strips before a search. Keep it.

### 2.2 Numbers never lead

A figure belongs inside a sentence, inside a table, or inside a chart, where it
carries context. It does not belong alone in a large tile.

Specifically banned:
- Rows of oversized bare figures (the `1,004 / 1.022 / 1.048 / +26` pattern)
- Any stat rendered at display size with no unit and no comparison
- Bold numbers scattered through running prose

**What replaced them:** a compact summary strip with a small uppercase label
above a normal-weight value, in a bordered row. Same information, one third the
visual weight. And where prose is needed, the sentence carries the figure:
"Move 50 of his 1,004 attempts out of the long mid-range and he scores +2.63
more per 100."

**Enforcement:** a test asserts zero `st.metric` widgets exist anywhere in the
app. Keep it.

### 2.3 Precision lives behind a click

Exact values, full tables, confidence intervals, model diagnostics: all of it
goes inside a collapsed disclosure labelled `Show the...`. The default view
carries the shape of the answer; the reader opens the panel when they want the
decimals.

This is the direct answer to "the numbers are too in your face." The numbers did
not get deleted, they got demoted.

### 2.4 Words only where a label cannot do the job

One line of clarification per page. No lede paragraphs, no narrative sections, no
essay structure. If a sentence is explaining what a column means, it should
probably be a glossary entry instead.

The one exception is the landing page, which gets two sentences explaining what
the product is (see §4.1). A visitor who does not know what they are looking at
cannot use a search box.

### 2.5 The navigation stays at four items or fewer

Every extra nav item is a decision the reader has to make before they can do
anything. Current structure:

| Item | Contains |
|---|---|
| **Players** | Landing page. Search, then that player's full sheet, including his prescription |
| **Leaders** | The whole league in one sortable table |
| **Teams** | All thirty, then any single team |
| **Findings** | The research results, plus method, guards and limits behind disclosure |

Consolidations already made, and why:
- The optimiser moved onto the player's own sheet. Someone already looking at a
  player's zone splits should not have to navigate elsewhere and search for him a
  second time to get "so what should he change."
- Method folded into Findings behind disclosure. It is credibility material, not
  a destination.

**Enforcement:** a test fails if the nav exceeds four options. Keep it.

---

## 3. Visual system

### 3.1 Surfaces and ink

| Role | Value | Note |
|---|---|---|
| Page plane | `#f9f9f7` | Never pure white |
| Card / table surface | `#fcfcfb` | Never pure white |
| Primary ink | `#0b0b0b` | |
| Secondary ink | `#52514e` | Body text |
| Muted | `#898781` | Captions, labels, axis text |
| Gridline | `#e1e0d9` | Hairlines, table row borders |
| Axis / border | `#c3c2b7` | |

Pure white (`#ffffff`) as a page background is a tell. The off-whites above are
deliberate.

### 3.2 Accent colours

| Role | Value |
|---|---|
| Primary accent (positive, links, active nav) | `#2a78d6` |
| Secondary series | `#eb6834` |
| Third series | `#1baf7a` |
| Negative values in tables | `#a83232` |
| Positive values in tables | `#1c5cab` |

**Do not change the chart palette.** These specific values were validated with a
colour-vision-deficiency checker: worst adjacent-pair separation ΔE 9.2 against a
target of 8, on the light surface. Swapping in brand colours (an ESPN red, for
instance) without re-running that validation will break the charts for
colour-blind readers. The stat-sheet feel comes from table chrome, not from
recolouring the data.

**Colour is never the sole carrier of meaning.** Signed values always print their
sign (`+12.2`, `−6.9`), so the red/blue treatment is redundant reinforcement
rather than the message.

### 3.3 Type

System sans only: `system-ui, -apple-system, "Segoe UI", sans-serif`.

Do not use Inter, Geist, or Space Grotesk. Those three fonts are the single most
reliable signal that a page was generated rather than designed.

| Element | Size | Weight | Notes |
|---|---|---|---|
| Kicker | 0.68rem | 620 | Uppercase, 0.15em tracking, muted |
| H1 | 1.62rem | 660 | −0.018em tracking |
| H2 | 1.04rem | 640 | |
| H3 | 0.95rem | 640 | |
| Body / note | 0.90rem | normal | 1.5 line-height, max 88ch |
| Caption | 0.78rem | normal | Muted |
| Table body | 0.84rem | normal | Tabular numerals |
| Table header | 0.64rem | 680 | Uppercase, 0.08em tracking |

The framework's default H1 is roughly 2.6rem, which is wildly out of proportion
against 1rem body text. Override it.

All numeric content uses `font-variant-numeric: tabular-nums` so columns align.

### 3.4 Shape and depth

- **Corner radius: 2–3px.** Not 8, not 12. Soft radii read as generated.
- **No drop shadows.** Depth comes from hairline borders (`1px solid` gridline).
- **No gradients** of any kind on chrome. The only gradient permitted is a
  validated diverging colour scale inside a chart.
- **No glass, blur, or translucency effects.**

### 3.5 Tables are the product

Tables get the box-score treatment:

- Header row: near-black background, white uppercase labels, sticky on scroll
- Zebra striping: alternating page-plane and surface
- All numeric columns right-aligned, tabular numerals
- Label columns left-aligned, slightly heavier weight
- Row hover: a faint blue wash (`#eef3fb`)
- Signed columns coloured blue/red as above
- Row padding 6px vertical, 11px horizontal. Dense, not airy.

**No heat-map gradients on table cells.** This was tried and removed: the cell
colouring competed with the charts for the same signal, and the page ended up
with two different colour languages saying the same thing.

---

## 4. Page patterns

### 4.1 The landing page

Order of elements, top to bottom:

1. Kicker (product name)
2. H1 stating what you can do here, in plain language
3. Two sentences explaining the product to someone who has never heard of it
4. A one-line glossary defining the two or three terms the tables use
5. Controls (season selector, search box)
6. Empty state until a search happens

The description must be readable by someone with no domain knowledge. The current
one:

> Two players can score the same. One is a better shooter; the other just gets
> easier shots. Shot Diet reads every shot of the last five seasons and splits a
> player's scoring into those two halves.

The glossary is a horizontal strip of `TERM — definition` pairs. It replaces what
would otherwise be a paragraph explaining the columns.

### 4.2 A subject sheet (player or team)

1. Name bar: H1 with a coloured left rule, meta line beneath (team, season)
2. Summary strip: 5–7 label/value cells in a bordered row
3. One line of clarification under the strip if the measures need it
4. Two-column body: visual on the left, table on the right
5. Secondary sections below
6. Disclosures at the bottom for ranks and detail

### 4.3 Empty states

A dashed border, surface background, muted text, and a sentence that says both
what to do and how much is available: "Search any of the 426 players in 2025-26.
Nothing loads until you pick one."

An empty state is not an error. It should feel like a starting line.

---

## 5. Copy rules

### 5.1 Punctuation

**No em dashes anywhere.** Not in the interface, not in documentation, not in
code comments. This is the most reliable single indicator of machine-written
text. Rewrite the sentence: use a comma, a colon, a semicolon, parentheses, or
two sentences. Substituting a hyphen in the same slot does not help, because the
rhythm is what gives it away.

No typographic ellipses (`…`) in data contexts. Write "to" in a range.

### 5.2 Banned constructions

- **"It's not X, it's Y."** Also its variants: "X is a Y problem, not a Z
  problem", "the gain is real; the personalisation is not". State the thing
  positively instead.
- **Triads used for rhythm.** "Faster, simpler, smarter."
- **Sentences that exist to sound like a conclusion** without adding information.

### 5.3 Tone

Plain, specific, declarative. Prefer the concrete number to the adjective. If a
sentence would survive being deleted, delete it.

Write out small numbers in prose where it reads naturally ("eleven attempts"),
but use numerals in any table, label, or comparison.

---

## 6. Anti-patterns

Check every screen against this list. These are the things that make a product
look generated. Most are cosmetic defaults that nobody chose.

**Never:**

| | |
|---|---|
| Harsh gradients | Lucide (or similar) stock icon sets |
| Pure white backgrounds | Rainbow / multi-hue accent colours |
| Drop shadows | Three feature cards in a row |
| Emoji in body copy or headings | Liquid glass / frosted effects |
| Em dashes | Inter, Geist, or Space Grotesk |
| Coloured left stripe on callouts | Fabricated testimonials |
| Bento grids | Fake terminal windows |
| "It's not X, it's Y" | Checkmark bullet lists |
| Three pricing tiers | Soft corner radii (8px+) |
| Purple-and-black palettes | Radial orbs / blurred blobs |
| Dot-grid backgrounds | Sparkle or "AI" icons |
| Animated arrows | Neon colours |
| Decorative hover animations | Generic pastel palettes |

**One clarification on emoji:** a single emoji as the browser favicon is fine and
is a thing real sites have. Emoji in headings, body text, or as bullet markers is
not.

**Decorative animation is banned outright.** A hero animation was built for this
product and then removed. Motion has to be doing work (a loading state, a
transition that explains where something went); if it exists to be impressive, it
reads as generated regardless of execution quality.

### 6.1 Things a finished product actually has

The inverse list. These are unglamorous and their absence is noticeable:

- A favicon
- Alt text on every image, describing content rather than saying "screenshot"
- Real loading and empty states
- Sensible behaviour at narrow widths
- Working search that handles the messy cases (see §7.1)
- Nothing broken in the console

Security hardening (CSRF, HSTS, CORS, rate limits, cookie banners), legal pages,
and SEO files are **not** applicable here and should not be added. This product
ships no server, no authentication, no database, and no user input storage.
Adding them would be a clearer sign of copied advice than anything on the banned
list.

---

## 7. Behaviour

### 7.1 Search must handle real names

Typing `jokic` must find `Nikola Jokić`. This is not a nicety. A naive
implementation filtering on exact label text fails for precisely the players
people look up most: Jokić, Dončić, Šengün, Porziņģis.

Implementation: normalise both the query and the candidate with Unicode NFKD
decomposition, strip combining marks, lowercase both sides, then substring match.

The result list shows enough context to pick correctly without clicking:
name, team, volume, and the headline measure. A single match auto-selects.

Once a subject is chosen, the search input is replaced by a "Showing X" line and
a **Clear** button. Do not leave a stale query sitting in a box next to the
results.

### 7.2 Controls

Explicit sort and filter controls, labelled in small uppercase. Sliders show
their value. Selectors default to the most recent season.

Where a table is rendered as HTML (and therefore loses click-to-sort), explicit
sort controls must be present to compensate.

---

## 8. Platform notes

These are specific to Streamlit and cost real time to discover. They will not be
obvious from documentation.

### 8.1 `st.dataframe` cannot be styled

It renders its grid to a **canvas**. CSS does not reach it. Cell background
colours via a pandas `Styler` do apply, but header styling, row striping,
alignment and typography do not.

If the tables need to look designed, render them as real HTML. The trade is
losing column-header click-sorting, which explicit sort controls cover.

### 8.2 Widget selectors depend on the build

This version renders widgets through **react-aria**, not BaseWeb. These selectors
match **nothing**:

```
[data-baseweb="select"]
[data-baseweb="tag"]
[data-baseweb="slider"]
[role="slider"]
[data-testid="stThumbValue"]
```

Working equivalents:

```
[data-testid="stSelectbox"] [role="group"]      /* the combobox shell */
[data-testid="stSliderThumbValue"]              /* the slider value bubble */
[data-testid="stRadioOption"]                   /* a radio option row */
[data-testid="stRadioOption"][data-selected="true"]   /* active state */
```

**Always verify a selector matches something before trusting it.** Three styling
rules in this codebase were dead for several iterations because they targeted
attributes that did not exist, and dead CSS fails silently.

### 8.3 Turning the sidebar radio into a nav

The radio dot is nested three divs deep inside the option label:

```
label > div > div > div:first-child
```

`label > div:first-child` does **not** work, because the label's first child is a
visually hidden input wrapper.

Use `[data-selected="true"]` on the label for the active state rather than
`:has(input:checked)`.

### 8.4 Slider colour

Comes from `theme.primaryColor` in `.streamlit/config.toml`, not from CSS. Set it
there.

### 8.5 Chrome to hide

```
[data-testid="stHeader"], [data-testid="stToolbar"]   /* Deploy button, menu */
#MainMenu, footer, [data-testid="stDecoration"]
```

### 8.6 Deprecations

`use_container_width` is deprecated. Use `width="stretch"`.

### 8.7 Testing

`AppTest` exposes accessors for markdown, dataframes, buttons, selectboxes,
sliders, expanders and metrics. **It has no accessor for plotly charts.** To
assert a chart did or did not render, test a proxy (the absence of tables plus
the presence of an empty-state marker).

`at.session_state` has no `.get()` method. Drive the UI through its widgets in
tests rather than inspecting state.

If headings are custom HTML rather than `st.title`, `at.title` will be empty.
Assert against the rendered markdown instead.

---

## 9. SVG animation notes

Retained only in case motion is ever justified. Both of these silently destroy a
rigged figure:

**Joint pivots.** `transform-box` defaults to `fill-box`, which pivots each group
on its own bounding box rather than on the joint. Every joint needs
`transform-box: view-box` with an explicit `transform-origin` in view-box
coordinates.

**Transform conflicts.** A CSS `transform` **replaces** an element's `transform`
attribute rather than composing with it. An element with `transform="translate(800,0)"`
that later receives a CSS transform snaps to the origin. Keep static offsets on an
outer wrapper group.

---

## 10. How to check your work

1. **Look at it.** Screenshot every page and actually inspect the image. Passing
   tests say nothing about layout. Defects found this way that tests missed
   include: a literal `undefined` printed on every chart, labels drawn
   off-canvas, a colour scale stretched by outliers until all signal washed out,
   and a table with its last column cut off.
2. **Search for `—` across the whole repository.** Expect zero.
3. **Verify every CSS selector matches at least one element.**
4. **Load the landing page and confirm nothing but the search box and the empty
   state is visible.**
5. **Run the test suite.** It should assert: every page renders, nothing loads
   before a search, accent-folded search works, sort controls reorder results,
   the nav has four or fewer items, and no bare stat tiles exist anywhere.
6. **Read the copy aloud.** Anything that sounds like marketing gets cut.
