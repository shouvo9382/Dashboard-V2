"""
scoring.py
==========
Pure data pipeline for the Bangladesh Sports Ministry athlete dashboard.

This module has NO Streamlit dependency so it can be unit-tested and reused.
It is responsible for:

  1. Reading the source Excel file (read-only; the file is never modified).
  2. Parsing the human-formatted string columns into clean numeric types.
  3. Deriving a transparent "health / availability" score from the free-text
     Injury History column via a documented keyword rubric.
  4. Deriving a "performance" ordinal from the expert-assigned Group/Tier grade.
  5. Computing a configurable, weighted OVERALL SCORE for every athlete and
     ranking each athlete WITHIN THEIR OWN SPORT.

--------------------------------------------------------------------------
THE OVERALL-SCORE FORMULA (documented in one place, easy to change)
--------------------------------------------------------------------------
Five components are computed for each athlete. Each component is turned into a
"higher-is-better" raw value, then normalised to a 0-100 scale *within the
athlete's own sport* (min-max, so a swimmer is compared only to swimmers).

    component            raw signal (higher = better)                weight
    -----------------    ------------------------------------------  ------
    performance          expert Group/Tier grade (Grade A / Tier 1    0.30
                         = best), inverted to higher-is-better
    fitness              composite of VO2 Max (+), Resting HR (-),    0.25
                         Body Fat (-)   [sub-weights below]
    health               availability score derived from the         0.20
                         Injury History text rubric
    training             training load proxy = calories Burned (+)    0.15
    nutrition            fuelling adequacy = closeness of the         0.10
                         Intake/Burn ratio to an ideal band          -----
                                                                 total 1.00

    fitness sub-weights: VO2 Max 0.50, Resting HR 0.25, Body Fat 0.25

    OVERALL = 100 * ( w_perf*perf_n + w_fit*fitness_n
                      + w_health*health_n + w_train*train_n
                      + w_nutr*nutrition_n )                 ->  range 0-100

Within each sport:
    RANK        = dense rank of OVERALL (1 = best)
    PERCENTILE  = share of same-sport athletes scoring at or below this athlete

All weights live in DEFAULT_WEIGHTS / DEFAULT_FITNESS_WEIGHTS below and can be
overridden at call time (the Streamlit UI passes live slider values in).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
#  CONFIGURATION  — change these to re-tune the model.                         #
# --------------------------------------------------------------------------- #

# Top-level component weights (the new 6-component government model).
# They are re-normalised to sum to 1.0 at runtime, so any positive numbers work.
DEFAULT_WEIGHTS: dict[str, float] = {
    "fitness": 0.30,       # VO2 / resting HR / body fat composite
    "career": 0.35,        # career win%, medals, national/international ranking
    "nutrition": 0.20,     # Intake/Burn fuelling adequacy
    "attendance": 0.05,    # training attendance
    "medical": 0.05,       # availability from injury history
    "coach": 0.05,         # divisional coach evaluation
}

# Ordered (label, weight_key, normalised_column) — the single source of truth the
# UI iterates over so the model lives in one place.
MODEL_COMPONENTS = [
    ("Fitness", "fitness", "fitness_n"),
    ("Career", "career", "career_n"),
    ("Nutrition", "nutrition", "nutrition_n"),
    ("Attendance", "attendance", "attendance_n"),
    ("Medical", "medical", "medical_n"),
    ("Coach Eval", "coach", "coach_n"),
]

# How the career sub-metrics combine into the single "career" component.
DEFAULT_CAREER_WEIGHTS: dict[str, float] = {
    "win_pct": 0.40,        # higher better
    "medals": 0.30,         # higher better
    "national_rank": 0.20,  # lower better
    "intl_rank": 0.10,      # lower better
}

# How the three fitness metrics combine into the single "fitness" component.
DEFAULT_FITNESS_WEIGHTS: dict[str, float] = {
    "vo2max": 0.50,      # higher is better
    "resting_hr": 0.25,  # lower is better
    "body_fat": 0.25,    # lower is better
}

# Nutrition: the Intake/Burn ratio considered "ideal" for a training athlete.
# A modest surplus supports recovery and adaptation; the score falls off as an
# athlete moves away from this band in either direction.
IDEAL_INTAKE_BURN_RATIO: float = 1.10

# Injury-History keyword rubric. Each pattern that matches subtracts points from
# a starting availability of 100. Order does not matter; every match is applied
# once. The result is clamped to [HEALTH_FLOOR, 100].
HEALTH_FLOOR: float = 45.0
INJURY_PENALTIES: list[tuple[str, float]] = [
    (r"\bchronic\b", 25),
    (r"\bcomplex\b", 18),
    (r"stress fracture", 20),
    (r"\bacl\b", 15),
    (r"prolonged|rehabilitation|arthroscopic|surgery|plating", 12),
    (r"restrict|workload restriction|restricted minutes", 12),
    (r"\bmissed\b", 12),
    (r"fracture", 8),
    (r"strain", 5),
    (r"sprain", 4),
    (r"tightness|stiffness|calluses|swelling|laceration|tweak", 4),
    (r"tendon|tendonitis|patellar|achilles|hamstring|groin|lumbar|metatarsal", 3),
    (r"manage|managed|management|tracking|monitoring|maintenance|preventive|preventative", 3),
]
# Phrases that indicate a fully clean bill of health -> no penalty at all.
CLEAN_HEALTH_PATTERNS: str = (
    r"clear medical|clear bill|no major|no historic|no historical|no recorded|"
    r"premium (physical )?fitness|clear medical profile|free of|free from|"
    r"clear medical log|no major limitations|no major structural"
)


# --------------------------------------------------------------------------- #
#  PARSING HELPERS                                                             #
# --------------------------------------------------------------------------- #

def _first_number(value: object) -> float:
    """Return the first numeric token in a string as a float, else NaN.

    Handles thousands separators ("3,400 kcal" -> 3400.0), decimals
    ("10.8%" -> 10.8) and unit suffixes ("178 cm (5'10\")" -> 178.0).
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    match = re.search(r"[-+]?\d[\d,]*\.?\d*", str(value))
    if not match:
        return np.nan
    return float(match.group().replace(",", ""))


def _tier_ordinal(group_tier: object) -> float:
    """Map an expert Group/Tier label to an ordinal where 1 = best.

    "Grade A ..."  -> 1, "Grade B" -> 2, "Grade C" -> 3, "Grade D" -> 4
    "Tier 1 ..."   -> 1, "Tier 2"  -> 2, ...
    Anything unrecognised returns NaN (later filled with the sport median).
    """
    if group_tier is None:
        return np.nan
    text = str(group_tier)
    m = re.search(r"Tier\s+(\d+)", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"Grade\s+([A-Z])", text, re.IGNORECASE)
    if m:
        return float(ord(m.group(1).upper()) - ord("A") + 1)
    return np.nan


def _health_score(injury_text: object) -> float:
    """Derive a 0-100 availability score from free-text injury history.

    A clean bill of health scores 100. Each risk keyword deducts points per the
    INJURY_PENALTIES rubric; the result is clamped to [HEALTH_FLOOR, 100].
    """
    if injury_text is None or (isinstance(injury_text, float) and np.isnan(injury_text)):
        return 100.0
    text = str(injury_text).lower()

    # Fully clean profiles are exempt from deductions.
    if re.search(CLEAN_HEALTH_PATTERNS, text):
        # Even "no major issues" wording occasionally co-occurs with a note;
        # give a near-perfect score rather than a hard 100.
        base_clean = 97.0
        return base_clean

    penalty = 0.0
    for pattern, points in INJURY_PENALTIES:
        if re.search(pattern, text):
            penalty += points

    # "fully recovered / cleared / healed / 100%" signals a resolved past issue:
    # cap the penalty so a currently-fit athlete is not over-punished.
    if re.search(r"fully (recovered|cleared|healed|restored|operational|stable|"
                 r"functional|fit|clear)|100%|now fully cleared", text):
        penalty = min(penalty, 20.0)

    return float(np.clip(100.0 - penalty, HEALTH_FLOOR, 100.0))


def _injury_status(injury_text: object) -> str:
    """Bucket the injury history into a short categorical for display/insights."""
    score = _health_score(injury_text)
    if score >= 95:
        return "Fully Fit"
    if score >= 80:
        return "Cleared / Recovered"
    if score >= 65:
        return "Actively Managed"
    return "Monitored / Restricted"


# --------------------------------------------------------------------------- #
#  LOAD + CLEAN                                                                #
# --------------------------------------------------------------------------- #

RAW_TO_CLEAN = {
    "Age": "age",
    "Height": "height_cm",
    "Weight": "weight_kg",
    "VO2 Max": "vo2max",
    "Resting HR": "resting_hr",
    "Body Fat": "body_fat",
    "Intake": "intake_kcal",
    "Burn": "burn_kcal",
}


def load_data(path: str | Path) -> pd.DataFrame:
    """Read the source workbook and return a cleaned, typed DataFrame.

    The source file is opened read-only and never modified. Unparseable numeric
    cells become NaN and are then filled with the per-sport median so that a
    single malformed cell never crashes a chart or the ranking.
    """
    df = pd.read_excel(path, sheet_name="Athletes", dtype=str)

    # The first column is unnamed in the source; it holds the cohort label.
    df.columns = [("Cohort" if str(c).strip() == "" else str(c).strip())
                  for c in df.columns]

    # --- SPORT SWAP (additive; the Excel file itself is never modified) ------
    # Remove the four retired sports and append the four new ones, generated in
    # code as rows in this same schema so the parsing below handles them too.
    import dataset  # local import keeps scoring.py importable on its own
    df = df[~df["Sport"].isin(dataset.REMOVED_SPORTS)].copy()
    new_rows = dataset.generate_new_sport_rows()
    df = pd.concat([df, new_rows], ignore_index=True)

    # Trim whitespace on text columns (skip nested/object carry columns).
    for col in df.columns:
        if col.startswith("_"):
            continue
        df[col] = df[col].astype("string").str.strip()

    # Parse the formatted numeric columns.
    for raw, clean in RAW_TO_CLEAN.items():
        if raw in df.columns:
            df[clean] = df[raw].map(_first_number)

    # Fill numeric gaps with the per-sport median (falls back to overall median).
    numeric_cols = list(RAW_TO_CLEAN.values())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df.groupby("Sport")[col].transform(
                lambda s: s.fillna(s.median())
            )
            df[col] = df[col].fillna(df[col].median())

    # Derived fields.
    df["energy_balance"] = df["intake_kcal"] - df["burn_kcal"]
    df["intake_burn_ratio"] = df["intake_kcal"] / df["burn_kcal"].replace(0, np.nan)
    df["tier_ordinal"] = df["Group/Tier"].map(_tier_ordinal)
    df["tier_ordinal"] = df.groupby("Sport")["tier_ordinal"].transform(
        lambda s: s.fillna(s.median())
    )
    df["tier_ordinal"] = df["tier_ordinal"].fillna(df["tier_ordinal"].median())
    df["health_score"] = df["Injury History"].map(_health_score)
    df["injury_status"] = df["Injury History"].map(_injury_status)

    # A short tier label for grouping/among charts, e.g. "Grade A", "Tier 1".
    df["tier_label"] = df["Group/Tier"].map(_short_tier_label)

    # --- EXTENDED PROFILES (personal/physical/career/medical/performance) ----
    # Additive: attaches new columns + nested career objects to every athlete.
    df = dataset.enrich_profiles(df)

    return df.reset_index(drop=True)


def _short_tier_label(group_tier: object) -> str:
    if group_tier is None:
        return "Unclassified"
    text = str(group_tier)
    m = re.search(r"(Tier\s+\d+)", text, re.IGNORECASE)
    if m:
        return m.group(1).title()
    m = re.search(r"(Grade\s+[A-Z])", text, re.IGNORECASE)
    if m:
        return m.group(1).title()
    return "Unclassified"


# --------------------------------------------------------------------------- #
#  NORMALISATION + SCORING                                                     #
# --------------------------------------------------------------------------- #

def _minmax_within_group(series: pd.Series, group: pd.Series,
                         higher_is_better: bool = True) -> pd.Series:
    """Min-max scale a series to 0-100 *within each group*.

    When every value in a group is identical (zero range) all members get 50,
    which keeps that component neutral rather than arbitrarily 0 or 100.
    """
    values = series if higher_is_better else -series

    def scale(block: pd.Series) -> pd.Series:
        lo, hi = block.min(), block.max()
        if pd.isna(lo) or pd.isna(hi) or hi == lo:
            return pd.Series(50.0, index=block.index)
        return (block - lo) / (hi - lo) * 100.0

    return values.groupby(group, group_keys=False).apply(scale)


def compute_scores(
    df: pd.DataFrame,
    weights: dict[str, float] | None = None,
    fitness_weights: dict[str, float] | None = None,
    ideal_ratio: float = IDEAL_INTAKE_BURN_RATIO,
) -> pd.DataFrame:
    """Attach normalised components, an OVERALL score, and within-sport rank.

    Parameters
    ----------
    df : cleaned DataFrame from load_data().
    weights : overrides for DEFAULT_WEIGHTS (any positive numbers; re-normalised).
    fitness_weights : overrides for DEFAULT_FITNESS_WEIGHTS.
    ideal_ratio : target Intake/Burn ratio for the nutrition component.

    Returns a COPY with these added columns:
        perf_n, fitness_n, health_n, training_n, nutrition_n   (0-100 each)
        overall_score                                          (0-100)
        sport_rank        (1 = best within sport, dense)
        sport_percentile  (0-100, share of sportmates at or below)
        sport_size        (number of athletes in that sport)
    """
    weights = _normalise_weights(weights or DEFAULT_WEIGHTS)
    fweights = _normalise_weights(fitness_weights or DEFAULT_FITNESS_WEIGHTS)
    cweights = _normalise_weights(DEFAULT_CAREER_WEIGHTS)
    out = df.copy()
    sport = out["Sport"]

    # --- informational: performance (expert tier) — kept for display only ----
    out["perf_n"] = _minmax_within_group(out["tier_ordinal"], sport,
                                         higher_is_better=False)

    # --- component: fitness (composite of three sub-metrics) -----------------
    vo2_n = _minmax_within_group(out["vo2max"], sport, higher_is_better=True)
    hr_n = _minmax_within_group(out["resting_hr"], sport, higher_is_better=False)
    bf_n = _minmax_within_group(out["body_fat"], sport, higher_is_better=False)
    out["vo2_n"], out["hr_n"], out["bf_n"] = vo2_n, hr_n, bf_n
    out["fitness_n"] = (
        fweights["vo2max"] * vo2_n
        + fweights["resting_hr"] * hr_n
        + fweights["body_fat"] * bf_n
    )

    # --- component: CAREER performance (new) ---------------------------------
    # Composite of win %, medals (higher better) and rankings (lower better),
    # each normalised within sport. Falls back gracefully if a field is absent.
    def _col(name, default=0.0):
        return out[name] if name in out.columns else pd.Series(default, index=out.index)
    win_n = _minmax_within_group(_col("career_win_pct"), sport, higher_is_better=True)
    med_n = _minmax_within_group(_col("career_medals"), sport, higher_is_better=True)
    nr_n = _minmax_within_group(_col("national_ranking", 15), sport, higher_is_better=False)
    ir_n = _minmax_within_group(_col("international_ranking", 300), sport, higher_is_better=False)
    out["career_n"] = (
        cweights["win_pct"] * win_n + cweights["medals"] * med_n
        + cweights["national_rank"] * nr_n + cweights["intl_rank"] * ir_n
    )

    # --- component: medical / availability (from injury text rubric) ---------
    out["health_n"] = _minmax_within_group(out["health_score"], sport,
                                           higher_is_better=True)
    out["medical_n"] = out["health_n"]  # alias for the model component name

    # --- informational: training load (calories burned) — display only -------
    out["training_n"] = _minmax_within_group(out["burn_kcal"], sport,
                                             higher_is_better=True)

    # --- component: training ATTENDANCE (new) --------------------------------
    out["attendance_n"] = _minmax_within_group(_col("training_attendance", 85),
                                               sport, higher_is_better=True)

    # --- component: COACH evaluation (new) -----------------------------------
    out["coach_n"] = _minmax_within_group(_col("coach_rating", 80), sport,
                                          higher_is_better=True)

    # --- component: nutrition (closeness of Intake/Burn ratio to ideal) ------
    ratio_gap = (out["intake_burn_ratio"] - ideal_ratio).abs()
    out["nutrition_n"] = _minmax_within_group(ratio_gap, sport,
                                              higher_is_better=False)

    # --- OVERALL weighted score (6-component government model) ----------------
    out["overall_score"] = (
        weights["fitness"] * out["fitness_n"]
        + weights["career"] * out["career_n"]
        + weights["nutrition"] * out["nutrition_n"]
        + weights["attendance"] * out["attendance_n"]
        + weights["medical"] * out["medical_n"]
        + weights["coach"] * out["coach_n"]
    ).round(2)

    # --- within-sport rank + percentile -------------------------------------
    out["sport_rank"] = (
        out.groupby("Sport")["overall_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )
    out["sport_percentile"] = (
        out.groupby("Sport")["overall_score"]
        .rank(pct=True, method="average")
        .mul(100)
        .round(1)
    )
    out["sport_size"] = out.groupby("Sport")["Sport"].transform("size")

    return out


def _normalise_weights(weights: dict[str, float]) -> dict[str, float]:
    """Return weights scaled to sum to 1.0 (guards against all-zero input)."""
    total = float(sum(max(0.0, v) for v in weights.values()))
    if total <= 0:
        n = len(weights)
        return {k: 1.0 / n for k in weights}
    return {k: max(0.0, v) / total for k, v in weights.items()}


# Convenience for quick manual testing: `python scoring.py <path>`
if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "data/Dashboard_Data.xlsx"
    frame = compute_scores(load_data(p))
    cols = ["Name", "Sport", "tier_label", "overall_score",
            "sport_rank", "sport_percentile", "injury_status"]
    print(frame.sort_values(["Sport", "sport_rank"])[cols].head(20).to_string(index=False))
