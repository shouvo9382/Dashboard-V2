# 🏅 Bangladesh Sports Ministry — National Athlete Performance Dashboard

A polished, demo-ready **Streamlit** SaaS dashboard for a national sports
ministry. It reads the athlete workbook directly (read-only), cleans the
human-formatted fields, and presents an executive summary, player profiles,
performance/fitness analytics, injury & training insights, calorie
intake-vs-burn analysis, and a **configurable within-sport ranking system with
a live leaderboard**.

Built for **218 athletes across 10 sports** (Cricket, Football, Athletics,
Archery, Swimming, Field Hockey, Basketball, Volleyball, Handball, Chess).

---

## 1. Quick start (run locally)

Requires **Python 3.10+**.

```bash
# 1. (optional) create an isolated environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. launch the app  (from inside this folder)
streamlit run app.py
```

Streamlit will open `http://localhost:8501` in your browser. If it does not
open automatically, copy the "Local URL" from the terminal.

> The dashboard loads `data/Dashboard_Data.xlsx`. To point it at a different
> file, edit `DATA_PATH` near the top of `app.py`. **The source workbook is
> never modified — it is opened strictly read-only.**

---

## 2. What's in the box

```
sports_dashboard/
├── app.py                 # Streamlit UI (5 pages, cascading filters, leaderboard)
├── scoring.py             # Pure data pipeline: parsing + ranking (fully documented)
├── requirements.txt       # Python dependencies
├── README.md              # this file
├── .streamlit/
│   └── config.toml        # government blue/green theme
├── assets/
│   └── emblem.svg         # original stylised emblem (not an official seal)
└── data/
    └── Dashboard_Data.xlsx  # unaltered copy of the source workbook
```

### Pages
1. **Executive Summary** — headline KPIs, athletes-by-sport, squad availability,
   and an average fitness-profile scatter.
2. **Player Profile** — cascading **Sport → Player** filters, a profile card
   with biometrics, a component radar, rank & percentile badges, and the
   athlete's calorie intake-vs-burn chart.
3. **Performance & Fitness** — VO₂/body-fat scatter, distributions, and a
   fitness-index leaderboard (respects the Sport filter).
4. **Injury & Training** — availability breakdown, training-load vs
   availability, and the **calorie intake-vs-burn** comparison.
5. **Rankings & Leaderboard** — the full within-sport leaderboard with a
   component breakdown; **updates live** as filters and weights change.

### Cascading filters
The sidebar **Player** dropdown only ever lists athletes from the selected
**Sport**. Choosing "All Sports" widens the pool; choosing a specific sport
narrows both the player list and every sport-scoped chart/leaderboard.

---

## 3. The ranking model (formula)

Every athlete receives an **Overall Score (0–100)** built from five components.
Each component is first turned into a *higher-is-better* raw value, then
**rescaled to 0–100 _within the athlete's own sport_** (min-max). Comparing
within sport is deliberate — a chess player's body-fat and a sprinter's are not
meaningfully comparable, so each athlete is judged only against their peers.

| Component | Signal (higher = better) | Default weight |
|---|---|---|
| **Performance** | expert **Group/Tier** grade — *Grade A / Tier 1 = best* (inverted to higher-is-better) | **30%** |
| **Fitness** | composite of **VO₂ Max** (+), **Resting HR** (−), **Body Fat** (−) | **25%** |
| **Health** | availability score derived from the free-text **Injury History** via a keyword rubric | **20%** |
| **Training** | **calories burned** per day (a training-load proxy) | **15%** |
| **Nutrition** | closeness of the **Intake / Burn** ratio to an ideal band (~1.10) | **10%** |

Fitness sub-weights: **VO₂ Max 50% · Resting HR 25% · Body Fat 25%**.

```
OVERALL = 100 × (  0.30·performanceₙ
                 + 0.25·fitnessₙ
                 + 0.20·healthₙ
                 + 0.15·trainingₙ
                 + 0.10·nutritionₙ )
```
(subscript ₙ = the component normalised to 0–100 within the sport)

Then, **within each sport**:
- **Rank** = position by overall score (1 = best; dense ranking, ties share a rank).
- **Percentile** = share of same-sport athletes scoring at or below this athlete.

### Health score from injury text
`Injury History` is free text, so a transparent, deterministic keyword rubric
turns it into a 0–100 availability score (see `INJURY_PENALTIES` and
`CLEAN_HEALTH_PATTERNS` in `scoring.py`). A clean bill of health scores ~97–100;
words like *chronic*, *stress fracture*, *restricted*, or *missed* deduct
points, while *fully recovered / 100% cleared* caps the penalty so a currently
fit athlete with a resolved past injury is not over-punished. Scores are
clamped to a floor so no one is zeroed out on text alone.

### Adjusting the weights
- **In the UI:** open **⚙️ Ranking model weights** in the sidebar and drag the
  sliders. Values auto-normalise to 100% and the whole dashboard — including the
  leaderboard — recomputes live.
- **In code:** edit `DEFAULT_WEIGHTS` and `DEFAULT_FITNESS_WEIGHTS` at the top
  of `scoring.py`. The nutrition target lives in `IDEAL_INTAKE_BURN_RATIO`.

---

## 4. Data handling notes

- **Read-only source.** The workbook is never written to; a copy lives in
  `data/` and is byte-identical to the file supplied.
- **Type inference.** Formatted strings like `"178 cm (5'10\")"`, `"3,400 kcal"`,
  and `"10.8%"` are parsed to clean numbers.
- **Missing values.** Any unparseable numeric cell is filled with the
  **per-sport median** (falling back to the overall median), so a single bad
  cell never breaks a chart or the ranking.
- **No fabricated data.** Every displayed metric is either taken directly from
  the workbook or derived by the documented model above.

---

## 5. Troubleshooting

- **`streamlit: command not found`** → activate your virtual environment, or run
  `python -m streamlit run app.py`.
- **Port already in use** → `streamlit run app.py --server.port 8502`.
- **File not found** → run the command from inside the `sports_dashboard`
  folder, or set an absolute `DATA_PATH` in `app.py`.

> **Note:** the leaderboard shades its cells with a hand-rolled RGBA gradient
> rather than `Styler.background_gradient`, so **matplotlib is not required**.
> Don't reintroduce `background_gradient` — it pulls in a ~30 MB dependency for
> a table shade and breaks clean installs built from `requirements.txt`.
