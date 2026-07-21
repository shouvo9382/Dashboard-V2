"""
dataset.py
==========
Data-model EXPANSION for the Bangladesh Ministry of Youth & Sports dashboard.

This module is additive. It does NOT touch the source Excel file and does NOT
change the scoring maths in scoring.py. It:

  1. Drops four sports (Handball, Basketball, Archery, Field Hockey) and adds
     four new ones (Badminton, Table Tennis, Kabaddi, Martial Arts), generating
     the new athletes as rows in the SAME schema the Excel uses, so the existing
     parsing/scoring pipeline handles them unchanged.
  2. Enriches EVERY athlete with the extended profile fields requested by the
     ministry (personal / physical / career / fitness / medical / performance),
     storing nested parts (career timeline, season stats, results, highlights,
     progress) as JSON-friendly Python objects inside the athlete record.
  3. Provides a divisional COACH database (8 divisions x every sport).

Design choices (agreed with the product owner):
  • Photos: a `photo_url` field exists but is left BLANK; the UI falls back to
    initial-avatars. Fill these later with licensed images.
  • Storage: nested data lives as objects inside each athlete record (option A).
  • Source: the Excel is kept; new sports are generated in code (option i).

DATA HONESTY
------------
Real Bangladesh player NAMES are used where verifiable (see REAL_PLAYERS). All
numeric statistics attached to them are ILLUSTRATIVE dummy values for structural
demonstration only — never presented as factual claims about real individuals.
Each athlete carries a `data_source` flag making this explicit:
    "real-name/illustrative-stats"  or  "dummy"
Everything is generated deterministically (seeded by athlete ID) so the numbers
are stable across reloads.
"""

from __future__ import annotations

import hashlib
import random

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
#  SPORT SWAP CONFIG                                                           #
# --------------------------------------------------------------------------- #
REMOVED_SPORTS = {"Handball", "Basketball", "Archery", "Field Hockey"}

DIVISIONS = ["Dhaka", "Chattogram", "Rajshahi", "Khulna",
             "Barishal", "Sylhet", "Rangpur", "Mymensingh"]

DISTRICTS = {
    "Dhaka": ["Dhaka", "Gazipur", "Narayanganj", "Tangail", "Faridpur"],
    "Chattogram": ["Chattogram", "Cox's Bazar", "Cumilla", "Feni", "Rangamati"],
    "Rajshahi": ["Rajshahi", "Bogura", "Pabna", "Natore", "Sirajganj"],
    "Khulna": ["Khulna", "Jashore", "Kushtia", "Satkhira", "Bagerhat"],
    "Barishal": ["Barishal", "Patuakhali", "Bhola", "Pirojpur", "Barguna"],
    "Sylhet": ["Sylhet", "Moulvibazar", "Habiganj", "Sunamganj"],
    "Rangpur": ["Rangpur", "Dinajpur", "Kurigram", "Nilphamari", "Gaibandha"],
    "Mymensingh": ["Mymensingh", "Jamalpur", "Netrokona", "Sherpur"],
}

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]

# Bengali name pools for generating dummy athletes/coaches (given + family).
_MALE_GIVEN = ["Rakib", "Sabbir", "Tanvir", "Jahid", "Nayeem", "Sohel", "Riad",
               "Mahmud", "Arif", "Rasel", "Shakil", "Emon", "Fahim", "Nuru",
               "Jubayer", "Hasib", "Mizanur", "Rakibul", "Sajjad", "Toriqul"]
_FEMALE_GIVEN = ["Nasrin", "Sultana", "Marzia", "Rehana", "Shabnam", "Farhana",
                 "Ruma", "Tania", "Sadia", "Mitu", "Lima", "Rupa", "Nabila",
                 "Sharmin", "Ayesha", "Jesmin", "Poly", "Rima", "Shila", "Munni"]
# Gender-neutral surnames usable for either gender.
_FAMILY_NEUTRAL = ["Ahmed", "Hossain", "Islam", "Rahman", "Chowdhury", "Uddin",
                   "Khan", "Sarkar", "Das", "Roy", "Miah", "Talukder", "Bhuiyan",
                   "Sheikh", "Molla", "Mondol"]
# Surnames conventionally used by women in Bangladesh.
_FAMILY_FEMALE = ["Akter", "Khatun", "Begum", "Parvin", "Sultana"]
# Back-compat alias (older code paths).
_FAMILY = _FAMILY_NEUTRAL


def _make_name(gender: str, rng: random.Random) -> str:
    """Build a gender-consistent Bangladeshi name.

    gender: 'M' or 'F'. Male names never take female-only surnames, and an
    optional 'Md ' honorific is only applied to male names.
    """
    if gender == "F":
        given = rng.choice(_FEMALE_GIVEN)
        fam = rng.choice(_FAMILY_NEUTRAL + _FAMILY_FEMALE)
        return f"{given} {fam}"
    given = rng.choice(_MALE_GIVEN)
    fam = rng.choice(_FAMILY_NEUTRAL)
    prefix = "Md " if rng.random() < 0.45 else ""
    return f"{prefix}{given} {fam}"

# --------------------------------------------------------------------------- #
#  REAL PLAYER NAMES (verifiable) — stats generated are illustrative only.     #
# --------------------------------------------------------------------------- #
# gender: M/F.  Kept modest and defensible; the rest are filled with dummies.
REAL_PLAYERS = {
    "Badminton": [
        ("Gourab Singha", "M", "Men's Singles"),
        ("Khandakar Abdus Soad", "M", "Men's Singles"),
        ("Abdul Zahir Tanbir", "M", "Men's Doubles"),
        ("Md Mizanur Rahman", "M", "Men's Doubles"),
        ("Urmi Akter", "F", "Women's Singles"),
        ("Nasima Khatun", "F", "Women's Doubles"),
        ("Konika Rani Adhikary", "F", "Women's Doubles"),
        ("Shapla Akter", "F", "Mixed Doubles"),
    ],
    "Table Tennis": [
        ("Muhtasin Ahmed Hridoy", "M", "Men's Singles"),
        ("Ramhim Lian Bawm", "M", "Men's Singles"),
        ("Khai Khai Marma", "F", "Women's Singles"),
        ("Sonam Sultana Soma", "F", "Women's Singles"),
        ("Mohutasin Ahmed Ridoy", "M", "Men's Doubles"),
    ],
    "Kabaddi": [
        ("Shahnaz Parvin Maleka", "F", "Raider / Captain"),
        ("Ziaur Rahman", "M", "Raider"),
        ("Md Arduzzaman Munshi", "M", "Corner Defender"),
        ("Sabuj Mia", "M", "All-Rounder"),
    ],
    "Martial Arts": [
        ("Al Amin Islam", "M", "Karate — Kumite"),
        ("Dipu Chakma", "M", "Taekwondo — Poomsae"),
        ("Masud Parvez", "M", "Taekwondo — Kyorugi"),
        ("Marzan Akter Priya", "F", "Karate — Kumite"),
        ("Humaira Akhter Antara", "F", "Karate — Kumite"),
    ],
}

# Per-sport generation profile: events, physiology ranges, club pool.
SPORT_PROFILE = {
    "Badminton": {
        "events": ["Men's Singles", "Women's Singles", "Men's Doubles",
                   "Women's Doubles", "Mixed Doubles"],
        "clubs": ["Bangladesh Ansar", "Bangladesh Army", "Bangladesh Biman",
                  "Wari Club", "Brothers' Union"],
        "height": (165, 185), "weight": (58, 78), "vo2": (48, 60),
        "hr": (46, 58), "bodyfat": (8, 15), "intake": (2700, 3300),
        "burn": (2500, 3100), "count": 20,
    },
    "Table Tennis": {
        "events": ["Men's Singles", "Women's Singles", "Men's Doubles",
                   "Women's Doubles"],
        "clubs": ["Bangladesh Biman", "Bangladesh Ansar", "Wari Club",
                  "Brothers' Union", "Abahani Limited"],
        "height": (160, 180), "weight": (55, 74), "vo2": (44, 55),
        "hr": (50, 62), "bodyfat": (9, 17), "intake": (2500, 3100),
        "burn": (2300, 2900), "count": 20,
    },
    "Kabaddi": {
        "events": ["Raider", "Corner Defender", "Cover Defender", "All-Rounder"],
        "clubs": ["Bangladesh Army", "BGB", "Bangladesh Ansar", "Bangladesh Police",
                  "Bangladesh Navy"],
        "height": (168, 186), "weight": (68, 92), "vo2": (50, 62),
        "hr": (48, 60), "bodyfat": (10, 18), "intake": (3100, 3800),
        "burn": (2900, 3600), "count": 20,
    },
    "Martial Arts": {
        "events": ["Karate — Kumite", "Karate — Kata", "Taekwondo — Kyorugi",
                   "Taekwondo — Poomsae", "Judo", "Wushu"],
        "clubs": ["Bangladesh Army", "Bangladesh Ansar", "BGB",
                  "Bangladesh Police", "Bangladesh Navy"],
        "height": (160, 185), "weight": (52, 85), "vo2": (50, 63),
        "hr": (44, 56), "bodyfat": (7, 14), "intake": (2600, 3300),
        "burn": (2500, 3200), "count": 20,
    },
}

SPORT_CODE = {"Badminton": "BD", "Table Tennis": "TT",
              "Kabaddi": "KB", "Martial Arts": "MA"}


def _seed(key: str) -> random.Random:
    """Deterministic RNG seeded by a string key (stable across runs)."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    return random.Random(h)


def _fmt_height(cm: int, rng: random.Random) -> str:
    inches_total = round(cm / 2.54)
    feet, inches = divmod(inches_total, 12)
    return f"{cm} cm ({feet}'{inches}\")"


# --------------------------------------------------------------------------- #
#  1) GENERATE NEW-SPORT ATHLETES  (raw Excel-schema rows)                     #
# --------------------------------------------------------------------------- #
def generate_new_sport_rows() -> pd.DataFrame:
    """Return new-sport athletes as raw rows matching the Excel column schema."""
    rows: list[dict] = []

    for sport, prof in SPORT_PROFILE.items():
        code = SPORT_CODE[sport]
        reals = REAL_PLAYERS.get(sport, [])
        n = prof["count"]

        roster: list[tuple[str, str, str, str]] = []  # (name, gender, event, source)
        for name, gender, event in reals:
            roster.append((name, gender, event, "real-name/illustrative-stats"))

        # Fill the remainder with deterministic dummy athletes.
        i = 0
        while len(roster) < n:
            rng = _seed(f"{sport}-dummy-{i}")
            gender = "M" if rng.random() < 0.55 else "F"
            name = _make_name(gender, rng)
            event = rng.choice(prof["events"])
            roster.append((name, gender, event, "dummy"))
            i += 1

        # Assign a within-sport performance rank to spread the tier grades.
        order = list(range(n))
        for idx, (name, gender, event, source) in enumerate(roster):
            aid = f"{code}-{idx + 1:02d}"
            rng = _seed(aid + name)

            # Tier grade: top ~20% A, next ~30% B, next ~30% C, rest D.
            q = idx / max(1, n - 1)
            grade = ("Grade A (Elite / National Team)" if q < 0.20 else
                     "Grade B (Senior National Pool)" if q < 0.50 else
                     "Grade C (Divisional Standout)" if q < 0.80 else
                     "Grade D (Development Squad)")

            height = rng.randint(*prof["height"])
            weight = rng.randint(*prof["weight"])
            vo2 = rng.randint(*prof["vo2"])
            hr = rng.randint(*prof["hr"])
            bodyfat = round(rng.uniform(*prof["bodyfat"]), 1)
            intake = rng.randint(prof["intake"][0] // 50, prof["intake"][1] // 50) * 50
            burn = rng.randint(prof["burn"][0] // 50, prof["burn"][1] // 50) * 50

            division = rng.choice(DIVISIONS)
            club = rng.choice(prof["clubs"])
            injuries = [
                "Clear medical log; premium fitness.",
                "Managed minor ankle sprain; fully recovered.",
                "Routine load monitoring; no restrictions.",
                "Recovered shoulder strain (2024); 100% cleared.",
                "Under preventive knee-management programme.",
                "No historic major injuries recorded.",
            ]
            injury = rng.choice(injuries)

            rows.append({
                "Cohort": f"{sport} Cohort ({n} Athletes)",
                "Group/Tier": grade,
                "ID": aid,
                "Name": name,
                "Sport": sport,
                "Position/Event": event,
                "Age": str(rng.randint(18, 32)),
                "Team/Club": f"{division} Division / {club}",
                "Recent Stats": _recent_stat(sport, rng),
                "Injury History": injury,
                "Height": _fmt_height(height, rng),
                "Weight": f"{weight} kg",
                "VO2 Max": f"{vo2} mL/kg/min",
                "Resting HR": f"{hr} BPM",
                "Body Fat": f"{bodyfat}%",
                "Intake": f"{intake:,} kcal",
                "Burn": f"{burn:,} kcal",
                # carried through so enrichment can use them
                "_gender": "Male" if gender == "M" else "Female",
                "_division": division,
                "_data_source": source,
            })

    return pd.DataFrame(rows)


def _recent_stat(sport: str, rng: random.Random) -> str:
    templates = {
        "Badminton": ["Reached national semi-final; strong smash accuracy.",
                      "Divisional champion; consistent rally control.",
                      "National doubles medallist; sharp net play."],
        "Table Tennis": ["Federation Cup quarter-finalist; fast topspin game.",
                         "National ranking climber; solid backhand block.",
                         "Divisional singles medallist; quick footwork."],
        "Kabaddi": ["High raid-success rate in national league.",
                    "Key defender; multiple super-tackles this season.",
                    "All-rounder; strong bonus-point conversion."],
        "Martial Arts": ["National kumite medallist; disciplined guard.",
                         "Divisional gold; strong poomsae precision.",
                         "Consistent podium finisher in weight class."],
    }
    return rng.choice(templates[sport])


# --------------------------------------------------------------------------- #
#  2) ENRICH EVERY ATHLETE WITH EXTENDED PROFILE FIELDS                        #
# --------------------------------------------------------------------------- #
def enrich_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Add the ministry's extended profile fields to every athlete row.

    Adds flat columns (gender, division, district, bmi, blood group, career
    tallies, rankings, ratings, etc.) and nested objects stored per-row
    (career_timeline, season_stats, national_results, international_results,
    career_highlights, career_progress). Deterministic by athlete ID.
    """
    out = df.copy()
    rec_gender, rec_div, rec_dist, rec_club, rec_natteam = [], [], [], [], []
    rec_bmi, rec_blood = [], []
    rec_matches, rec_wins, rec_losses, rec_medals = [], [], [], []
    rec_natrank, rec_intrank = [], []
    rec_perf, rec_fit, rec_attend = [], [], []
    rec_emergency, rec_photo, rec_source = [], [], []
    base_anchor = {}
    rec_winpct, rec_medalpct, rec_best, rec_worst = [], [], [], []
    rec_timeline, rec_season, rec_natres, rec_intres = [], [], [], []
    rec_highlights, rec_progress = [], []

    for _, a in out.iterrows():
        aid = str(a["ID"])
        rng = _seed("enrich-" + aid + str(a["Name"]))
        sport = str(a["Sport"])

        # Gender: use carried value if present (new sports), else deterministic.
        gender = a.get("_gender")
        if not isinstance(gender, str) or gender not in ("Male", "Female"):
            gender = "Male" if rng.random() < 0.6 else "Female"

        # Division: parse from Team/Club when possible, else carried/random.
        division = a.get("_division")
        team = str(a.get("Team/Club", ""))
        if not isinstance(division, str) or division not in DIVISIONS:
            division = next((d for d in DIVISIONS if d in team), None) or rng.choice(DIVISIONS)
        district = rng.choice(DISTRICTS[division])

        club = team.split("/")[-1].strip() if "/" in team else (team or "National Club")
        national_team = "Bangladesh National Team"

        # Physical
        h = float(a.get("height_cm") or 172)
        w = float(a.get("weight_kg") or 68)
        bmi = round(w / ((h / 100) ** 2), 1) if h else np.nan

        # Performance & fitness ratings (0-100), tied to tier where available.
        tier = str(a.get("tier_label", ""))
        base = {"Grade A": 88, "Tier 1": 88, "Grade B": 78, "Tier 2": 78,
                "Grade C": 68, "Tier 3": 68, "Grade D": 58, "Tier 4": 58}
        anchor = next((v for k, v in base.items() if k in tier or k in str(a.get("Group/Tier", ""))), 72)
        base_anchor[str(a["ID"])] = anchor
        perf_rating = int(np.clip(anchor + rng.randint(-6, 6), 40, 99))
        fit_rating = int(np.clip(anchor + rng.randint(-8, 8), 40, 99))
        attendance = int(np.clip(rng.gauss(88, 6), 60, 100))

        # Career tallies — internally consistent.
        years_active = rng.randint(3, 12)
        matches = years_active * rng.randint(8, 22)
        win_rate = np.clip((perf_rating - 40) / 60 * 0.55 + rng.uniform(0.15, 0.35), 0.2, 0.85)
        wins = int(matches * win_rate)
        losses = matches - wins
        medals = int(np.clip(round(wins / rng.randint(6, 12)), 0, 40))
        nat_rank = rng.randint(1, 25)
        int_rank = rng.randint(40, 600)

        win_pct = round(wins / matches * 100, 1) if matches else 0.0
        medal_pct = round(medals / matches * 100, 1) if matches else 0.0

        # Nested career objects.
        start_year = 2026 - years_active
        timeline = []
        for yr in range(start_year, 2026):
            timeline.append({
                "year": yr,
                "event": rng.choice([
                    "National Championship", "Divisional Meet", "SA Games trial",
                    "Federation Cup", "Inter-Club League", "National Games"]),
                "result": rng.choice(["Gold", "Silver", "Bronze", "4th",
                                      "Semi-final", "Quarter-final", "Participated"]),
            })

        seasons = []
        for s in range(min(5, years_active)):
            yr = 2025 - s
            sm = rng.randint(6, 20)
            sw = int(sm * np.clip(win_rate + rng.uniform(-0.1, 0.1), 0.1, 0.95))
            seasons.append({"season": f"{yr}", "matches": sm, "wins": sw,
                            "losses": sm - sw,
                            "rating": int(np.clip(anchor + rng.randint(-10, 10), 40, 99))})
        seasons = list(reversed(seasons))

        nat_results = [
            {"year": rng.randint(start_year, 2025),
             "competition": "National Championship",
             "result": rng.choice(["Champion", "Runner-up", "Semi-finalist"])}
            for _ in range(rng.randint(2, 4))
        ]
        int_results = [
            {"year": rng.randint(max(start_year, 2016), 2025),
             "competition": rng.choice(["SA Games", "Asian Championship",
                                        "Commonwealth event", "Islamic Sol. Games"]),
             "result": rng.choice(["Gold", "Silver", "Bronze", "Group stage",
                                   "Round of 16", "Did not medal"])}
            for _ in range(rng.randint(1, 3))
        ]

        highlights = rng.sample([
            "National title holder", "Represented Bangladesh internationally",
            "Divisional record holder", "Youngest medallist in category",
            "Multiple-season top performer", "National camp scholarship",
            "Federation Cup medallist", "Selected for high-performance unit",
        ], k=rng.randint(2, 4))

        progress = [{"year": yr,
                     "rating": int(np.clip(anchor + rng.randint(-14, 6) + i * rng.randint(0, 3),
                                           40, 99))}
                    for i, yr in enumerate(range(start_year, 2026))]

        best = max(int_results + nat_results,
                   key=lambda r: {"Gold": 6, "Champion": 6, "Silver": 5,
                                  "Runner-up": 5, "Bronze": 4, "Semi-finalist": 3,
                                  "Semi-final": 3}.get(r["result"], 1),
                   default={"competition": "—", "result": "—", "year": ""})
        worst = min(int_results + nat_results,
                    key=lambda r: {"Gold": 6, "Champion": 6, "Silver": 5,
                                   "Runner-up": 5, "Bronze": 4}.get(r["result"], 1),
                    default={"competition": "—", "result": "—", "year": ""})

        # Emergency contact — synthetic, clearly fake.
        emergency = f"+8801{rng.randint(3,9)}{rng.randint(10**7, 10**8-1)}"

        rec_gender.append(gender)
        rec_div.append(division)
        rec_dist.append(district)
        rec_club.append(club)
        rec_natteam.append(national_team)
        rec_bmi.append(bmi)
        rec_blood.append(rng.choice(BLOOD_GROUPS))
        rec_matches.append(matches)
        rec_wins.append(wins)
        rec_losses.append(losses)
        rec_medals.append(medals)
        rec_natrank.append(nat_rank)
        rec_intrank.append(int_rank)
        rec_perf.append(perf_rating)
        rec_fit.append(fit_rating)
        rec_attend.append(attendance)
        rec_emergency.append(emergency)
        rec_photo.append("")  # blank on purpose; UI falls back to avatar
        rec_source.append(a.get("_data_source", "dummy" if sport in SPORT_PROFILE else "source-dataset"))
        rec_winpct.append(win_pct)
        rec_medalpct.append(medal_pct)
        rec_best.append(f"{best['result']} — {best['competition']} ({best['year']})")
        rec_worst.append(f"{worst['result']} — {worst['competition']} ({worst['year']})")
        rec_timeline.append(timeline)
        rec_season.append(seasons)
        rec_natres.append(nat_results)
        rec_intres.append(int_results)
        rec_highlights.append(highlights)
        rec_progress.append(progress)

    out["gender"] = rec_gender
    out["division"] = rec_div
    out["district"] = rec_dist
    out["club"] = rec_club
    out["national_team"] = rec_natteam
    out["bmi"] = rec_bmi
    out["blood_group"] = rec_blood
    out["career_matches"] = rec_matches
    out["career_wins"] = rec_wins
    out["career_losses"] = rec_losses
    out["career_medals"] = rec_medals
    out["national_ranking"] = rec_natrank
    out["international_ranking"] = rec_intrank
    out["performance_rating"] = rec_perf
    out["fitness_rating"] = rec_fit
    out["training_attendance"] = rec_attend
    out["emergency_contact"] = rec_emergency
    out["photo_url"] = rec_photo
    out["data_source"] = rec_source
    # Divisional coach evaluation attached to the athlete (matches coach DB).
    out["coach_rating"] = [coach_rating_for(str(s), str(d))
                           for s, d in zip(out["Sport"], out["division"])]
    # Sport-specific career statistics (cricket runs/wickets, football goals, etc.)
    out["sport_stats"] = [
        generate_sport_stats(str(s), str(e), str(i),
                             float(base_anchor.get(str(i), 72)), int(m))
        for s, e, i, m in zip(out["Sport"], out["Position/Event"],
                              out["ID"], out["career_matches"])
    ]
    out["career_win_pct"] = rec_winpct
    out["career_medal_pct"] = rec_medalpct
    out["best_performance"] = rec_best
    out["worst_performance"] = rec_worst
    out["career_timeline"] = rec_timeline
    out["season_stats"] = rec_season
    out["national_results"] = rec_natres
    out["international_results"] = rec_intres
    out["career_highlights"] = rec_highlights
    out["career_progress"] = rec_progress

    # Drop internal carry columns.
    for c in ["_gender", "_division", "_data_source"]:
        if c in out.columns:
            out = out.drop(columns=c)
    return out


# --------------------------------------------------------------------------- #
#  3) COACH DATABASE  (8 divisions x every sport)                             #
# --------------------------------------------------------------------------- #
COACH_LICENSES = ["BOA Level I", "BOA Level II", "BOA Level III (Elite)",
                  "AFC/Asian Federation Certified", "International Instructor"]
COACH_EDU = ["BPEd, National College of PE & Sports", "MSc Sports Science, DU",
             "BSc Physical Education, JU", "Diploma in Coaching, BKSP",
             "MPEd, Rajshahi University"]


# Verified real national head coaches (searched; sourced). Only solidly
# confirmed entries go here — everything else is realistic dummy.
VERIFIED_NATIONAL_COACHES = {
    "Cricket": ("Phil Simmons", "National Head Coach (verified — BCB, to 2027)"),
}


def load_coaches(sports: list[str]) -> pd.DataFrame:
    """Build 10 coaches per sport: 8 divisional + National Head + Assistant.

    Divisional coaches are realistic dummy profiles (real local coach names are
    not publicly documented). The National Head Coach uses a VERIFIED real name
    where one is confirmed; otherwise it is dummy. Each row carries a
    `data_source` flag so verified vs illustrative is explicit.
    """
    rows = []
    for sport in sports:
        # --- National-level (2 coaches) ---
        verified = VERIFIED_NATIONAL_COACHES.get(sport)
        for slot, role in enumerate(["National Head Coach", "National Assistant Coach"]):
            rng = _seed(f"natcoach-{sport}-{slot}")
            is_verified = (slot == 0 and verified)
            if is_verified:
                cname, note = verified
                gender = "Male"
                source = "verified"
            else:
                g = "M" if rng.random() < 0.75 else "F"
                cname = _make_name(g, rng)
                gender = "Male" if g == "M" else "Female"
                note = role
                source = "illustrative"
            exp = rng.randint(12, 32)
            # For a verified real coach, don't fabricate personal contact/education.
            if is_verified:
                education = "—"
                phone = "—"
                email = "Via national federation"
            else:
                education = rng.choice(COACH_EDU)
                phone = f"+8801{rng.randint(3,9)}{rng.randint(10**7, 10**8-1)}"
                email = f"{sport[:2].lower()}.national@moys.gov.bd"
            rows.append({
                "sport": sport, "division": "National",
                "name": cname, "role": role,
                "gender": gender,
                "age": ("—" if is_verified else exp + rng.randint(26, 34)),
                "experience_years": exp,
                "license": "AFC/International Pro Licence",
                "certificates": rng.sample(
                    ["High-Performance Coaching", "Sports Nutrition L3",
                     "Advanced S&C", "Anti-Doping (WADA)", "Talent ID Certified"],
                    k=3),
                "achievements": rng.sample(
                    ["National-team head/assistant role", "Guided athletes to SA Games podium",
                     "Built national development pipeline", "International tournament experience"],
                    k=2),
                "education": education,
                "specialization": _coach_spec(sport, rng),
                "current_athletes": rng.randint(18, 40),
                "phone": phone,
                "email": email,
                "performance_rating": int(np.clip(rng.gauss(88, 5), 70, 99)),
                "photo_url": "",
                "data_source": source,
            })
        # --- Divisional (8 coaches) ---
        for division in DIVISIONS:
            rng = _seed(f"coach-{sport}-{division}")
            g = "M" if rng.random() < 0.7 else "F"
            name = _make_name(g, rng)
            gender = "Male" if g == "M" else "Female"
            experience = rng.randint(5, 28)
            rating = coach_rating_for(sport, division)
            n_athletes = rng.randint(6, 24)
            certs = rng.sample([
                "NSC Advanced Coaching", "Sports Nutrition Level 2",
                "Strength & Conditioning Cert.", "Anti-Doping (WADA) Certified",
                "Sports Psychology Workshop", "First-Aid & Rehab Certified"],
                k=rng.randint(2, 4))
            achievements = rng.sample([
                "Produced 3+ national medallists", "Divisional Coach of the Year",
                "Led team to National Games podium", "Developed youth pipeline",
                "SA Games support-staff experience", "20+ athletes to national camp"],
                k=rng.randint(2, 3))
            slug = f"{sport[:2].lower()}.{division[:3].lower()}"
            rows.append({
                "sport": sport,
                "division": division,
                "name": name,
                "role": f"{division} Divisional Coach",
                "data_source": "illustrative",
                "gender": gender,
                "age": experience + rng.randint(24, 32),
                "experience_years": experience,
                "license": rng.choice(COACH_LICENSES),
                "certificates": certs,
                "achievements": achievements,
                "education": rng.choice(COACH_EDU),
                "specialization": _coach_spec(sport, rng),
                "current_athletes": n_athletes,
                "phone": f"+8801{rng.randint(3,9)}{rng.randint(10**7, 10**8-1)}",
                "email": f"{slug}.coach@moys.gov.bd",
                "performance_rating": rating,
                "photo_url": "",  # blank; UI falls back to avatar
            })
    return pd.DataFrame(rows)


def _coach_spec(sport: str, rng: random.Random) -> str:
    generic = ["Technique & fundamentals", "Strength & conditioning",
               "Youth development", "High-performance / elite prep",
               "Tactical analysis", "Rehabilitation & load management"]
    return rng.choice(generic)


def coach_rating_for(sport: str, division: str) -> int:
    """Deterministic divisional-coach performance rating (0-100).

    Shared by load_coaches() and enrich_profiles() so an athlete's "coach
    evaluation" component always matches their division coach's rating.
    """
    rng = _seed(f"coachrating-{sport}-{division}")
    return int(np.clip(rng.gauss(80, 8), 55, 99))


# --------------------------------------------------------------------------- #
#  4) AI RECOMMENDATION ENGINE  (rule-based, adapts to each athlete's stats)   #
# --------------------------------------------------------------------------- #
# This is a transparent, deterministic rules engine — not a black-box model.
# It reads the athlete's own normalised components (0-100 vs same-sport peers)
# and raw physiology, then emits targeted guidance. Documented so a coach can
# see exactly why each recommendation fired.

_COMPONENT_LABELS = {
    "fitness_n": "Fitness", "career_n": "Career", "nutrition_n": "Nutrition",
    "attendance_n": "Attendance", "medical_n": "Availability", "coach_n": "Coach eval",
}


def generate_recommendations(a) -> dict:
    """Return a dict of 9 personalized recommendation fields for one athlete.

    `a` is a scored athlete row (pandas Series) with normalised components and
    raw physiology already attached. All thresholds are explicit below.
    """
    def g(k, default=0.0):
        v = a.get(k, default)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    comps = {k: g(k) for k in _COMPONENT_LABELS}
    ranked = sorted(comps.items(), key=lambda kv: kv[1], reverse=True)
    strengths = [f"{_COMPONENT_LABELS[k]} ({v:.0f}/100)" for k, v in ranked[:2] if v >= 55]
    weaknesses = [f"{_COMPONENT_LABELS[k]} ({v:.0f}/100)" for k, v in ranked[::-1][:2] if v < 60]
    if not strengths:
        strengths = [f"{_COMPONENT_LABELS[ranked[0][0]]} ({ranked[0][1]:.0f}/100)"]

    # Values used by the rule logic (read directly; some are informational-only
    # columns not part of the weighted model).
    fitness_n = g("fitness_n"); health_n = g("medical_n"); training_n = g("training_n")
    nutrition_n = g("nutrition_n")
    vo2 = g("vo2max"); rhr = g("resting_hr"); bf = g("body_fat")
    eb = g("energy_balance"); attend = g("training_attendance", 85)
    status = str(a.get("injury_status", ""))
    sport = str(a.get("Sport", "")); event = str(a.get("Position/Event", ""))

    # --- Fitness recommendation ---
    if fitness_n < 45 or vo2 < 50:
        fitness = ("Aerobic base is the priority. Add 2–3 zone-2 sessions/week "
                   f"(30–45 min) to lift VO₂ Max from ~{vo2:.0f}; recheck in 8 weeks.")
    elif rhr >= 58:
        fitness = (f"Resting HR ({rhr:.0f} BPM) suggests recovery headroom. Add "
                   "steady-state cardio and monitor morning HR for downward trend.")
    else:
        fitness = ("Fitness base is solid. Shift to sport-specific interval work "
                   "to convert aerobic capacity into on-field repeat-effort ability.")

    # --- Training recommendation ---
    if training_n < 45:
        training = ("Training load is below peer norm. Progress weekly volume ~10% "
                    "with periodised blocks; avoid single large jumps.")
    elif attend < 80:
        training = (f"Attendance ({attend:.0f}%) is limiting adaptation. Tighten "
                    "session consistency before adding intensity.")
    else:
        training = ("Load and attendance are healthy. Introduce a deload every 4th "
                    "week to consolidate gains and reduce overuse risk.")

    # --- Recovery recommendation ---
    if status in ("Monitored / Restricted", "Actively Managed") or health_n < 50:
        recovery = ("Availability is the limiter. Prioritise physio-led rehab, "
                    "cap high-impact volume, and clear return-to-play gates before load spikes.")
    elif rhr >= 58:
        recovery = ("Add structured recovery: 8+ h sleep, mobility, and one full "
                    "rest day; track HRV/resting-HR to confirm adaptation.")
    else:
        recovery = ("Recovery status is good. Maintain sleep hygiene and routine "
                    "soft-tissue work to protect the current low injury risk.")

    # --- Diet recommendation ---
    if bf >= 15:
        diet = (f"Body fat ({bf:.1f}%) is above the competitive band. Apply a modest "
                "300–400 kcal deficit with protein at 1.8–2.2 g/kg to preserve lean mass.")
    elif eb < -100:
        diet = (f"Energy balance is negative ({eb:+.0f} kcal). Increase intake to "
                "meet training demand and protect recovery and immune function.")
    elif nutrition_n < 50:
        diet = ("Fuelling timing needs work. Anchor carbs around sessions and add a "
                "recovery shake (3:1 carb:protein) within 30 min post-training.")
    else:
        diet = ("Nutrition is well-matched to load. Maintain current fuelling and "
                "hydrate to bodyweight loss during heavy blocks.")

    # --- Technical recommendation (sport/position aware) ---
    tech_map = {
        "Badminton": "Sharpen net-kill accuracy and rear-court smash consistency; add multi-shuttle drills.",
        "Table Tennis": "Drill third-ball attack and backhand-block transitions; add serve-variation sets.",
        "Kabaddi": "Refine raid footwork and escape timing; build super-tackle coordination in defence.",
        "Martial Arts": "Tighten guard-to-counter timing and scoring-zone precision; add reaction drills.",
        "Cricket": "Situational net work — match-scenario batting/bowling under fatigue.",
        "Football": "Position-specific decision drills and repeat-sprint finishing.",
        "Athletics": "Event-specific technical model refinement with video feedback.",
        "Swimming": "Stroke-efficiency and turn/underwater work to cut split times.",
        "Chess": "Opening-repertoire depth and endgame conversion under time pressure.",
        "Volleyball": "Serve-receive platform control and attack-approach timing.",
    }
    technical = tech_map.get(sport, "Refine core sport-specific skills with video-based feedback.")
    if event and sport in ("Badminton", "Table Tennis", "Martial Arts", "Kabaddi"):
        technical = f"({event}) " + technical

    # --- Mental coaching recommendation ---
    seasons = a.get("season_stats") or []
    ratings = [s.get("rating", 0) for s in seasons] if isinstance(seasons, list) else []
    variance = (max(ratings) - min(ratings)) if len(ratings) >= 2 else 0
    pct = g("sport_percentile", 50)
    if variance >= 20:
        mental = ("Performance is inconsistent season-to-season. Add routine "
                  "building and pre-competition visualisation to stabilise output.")
    elif pct >= 80:
        mental = ("Elite standing brings pressure. Focus on process goals and "
                  "controlled arousal to sustain top-percentile results.")
    else:
        mental = ("Build competitive confidence with graded exposure to higher-level "
                  "meets and structured post-match reflection.")

    # --- Expected improvement (quantified) ---
    # If the two weakest components rose to ~65, estimate the overall-score uplift
    # using the model's own default weights.
    from scoring import DEFAULT_WEIGHTS
    wmap = {"fitness_n": "fitness", "career_n": "career", "nutrition_n": "nutrition",
            "attendance_n": "attendance", "medical_n": "medical", "coach_n": "coach"}
    uplift = 0.0
    for k, v in ranked[::-1][:2]:
        target = max(v, 65.0)
        uplift += (target - v) * DEFAULT_WEIGHTS[wmap[k]]
    cur = g("overall_score", 0.0)
    proj = min(100.0, cur + uplift)
    expected = (f"Addressing the two weakest areas could lift the overall score "
                f"from {cur:.0f} to ≈{proj:.0f} (+{proj - cur:.0f}) over a training block.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses or ["No component below peer norm — maintain broadly."],
        "fitness": fitness,
        "training": training,
        "recovery": recovery,
        "diet": diet,
        "technical": technical,
        "mental": mental,
        "expected_improvement": expected,
        "projected_overall": round(proj, 1),
        "current_overall": round(cur, 1),
    }


# --------------------------------------------------------------------------- #
#  5) NEWS CENTER  (real, sourced articles — never fabricated)                 #
# --------------------------------------------------------------------------- #
# Every item below is a factual summary of a real, published Prothom Alo
# article, attributed with source + date + URL. Headlines/summaries are English
# renderings of the reporting; nothing is invented. To add more, append dicts
# in the same shape. `image_url` may be blank -> a category banner is shown.

NEWS_ITEMS = [
    {
        "headline": "27 sports federations get new ad-hoc committees; elections ordered within three months",
        "summary": ("The government dissolved the interim-era ad-hoc committees of 27 "
                    "federations — including badminton, table tennis, kabaddi, judo, "
                    "taekwondo, karate and chess — and formed new ones, instructing them "
                    "to hold elections within three months. New general secretaries were "
                    "named across federations (chess: GM Niaz Morshed; badminton: Hasibur "
                    "Rahman Shakil; table tennis: Saidul Haque Sadi)."),
        "date": "2026-07-18", "category": "Governance", "priority": "High",
        "source": "Prothom Alo",
        "url": "https://www.prothomalo.com/sports/other-sports/hvu5wwzmuw",
        "image_url": "https://media.prothomalo.com/prothomalo-bangla%2F2025-10-28%2Fjl4vcfdb%2Fimage_221939_1754369241.jpg?rect=75%2C0%2C675%2C450&w=622&auto=format%2Ccompress&fmt=avif",
    },
    {
        "headline": "‘Notun Kudi’ national talent-hunt finals begin; PM to attend closing",
        "summary": ("The Ministry of Youth & Sports’ nationwide talent-search program holds "
                    "its national finals across four Dhaka venues, concluding 27 July at "
                    "Army Stadium. Top selected athletes will receive long-term advanced "
                    "training and direct BKSP admission. Junior & Sports Minister Aminul "
                    "Haque announced the program; the Prime Minister is to attend the closing."),
        "date": "2026-07-07", "category": "Development", "priority": "High",
        "source": "Prothom Alo",
        "url": "https://www.prothomalo.com/sports/football/oyds04klie",
        "image_url": "https://media.prothomalo.com/prothomalo-bangla%2F2026-07-07%2Fp0fpi99w%2FWhatsApp-Image-2026-07-07-at-6.31.49-PM.jpeg?rect=0%2C0%2C1600%2C1067&w=622&auto=format%2Ccompress&fmt=avif",
    },
    {
        "headline": "Shaheed Chandu Stadium (Bogura) to regain international cricket-venue status",
        "summary": ("Junior & Sports Minister Aminul Haque announced development work to "
                    "restore Bogura’s Shaheed Chandu Stadium to an international-standard "
                    "cricket venue following ICC/BCB guidelines, as part of a plan to build "
                    "‘sports villages’ across 64 districts. A women’s BPL is planned there."),
        "date": "2026-04-13", "category": "Infrastructure", "priority": "Medium",
        "source": "Prothom Alo",
        "url": "https://www.prothomalo.com/bangladesh/district/xvj0bv3qtd",
        "image_url": "https://media.prothomalo.com/prothomalo-bangla%2F2026-04-13%2F0y7dbxc0%2FBoguraDH049320260413Bogura-Sports-2.jpg?rect=30%2C0%2C1223%2C815&w=622&auto=format%2Ccompress&fmt=avif",
    },
    {
        "headline": "Free freelancing-training courses launched across 64 districts",
        "summary": ("Under a government project, e-Learning and Earning Ltd. began free "
                    "three-month freelancing training in all 64 districts, inaugurated "
                    "virtually by Junior & Sports Minister Aminul Haque. The sixth batch "
                    "trains 4,800 youths (75 per district), aged 18–35 with at least HSC."),
        "date": "2026-04-02", "category": "Youth", "priority": "Medium",
        "source": "Prothom Alo",
        "url": "https://www.prothomalo.com/technology/freelancing/lytsysy0bz",
        "image_url": "https://media.prothomalo.com/prothomalo-bangla%2F2026-05-17%2F73p2m0mt%2FWhatsApp-Image-2026-05-17-at-8.19.37-PM.jpeg?rect=80%2C0%2C912%2C608&w=622&auto=format%2Ccompress&fmt=avif",
    },
    {
        "headline": "Which team PM Tarique Rahman supports at the FIFA World Cup",
        "summary": ("PM and BNP Chairman Tarique Rahman hinted at supporting England at the "
                    "2026 FIFA World Cup while speaking with reporters in Dhaka, without "
                    "naming a team directly."),
        "date": "2026-06-16", "category": "Football", "priority": "Low",
        "source": "Prothom Alo",
        "url": "https://en.prothomalo.com/sports/football/zms45t3gmt",
        "image_url": ("https://media.prothomalo.com/prothomalo-english%2F2026-06-16%2F"
                      "29svhrnc%2Fprothomalo-english2025-12-14blzwfzxjTarique-Rahman.avif"
                      "?w=1200&ar=16%3A9&auto=format%2Ccompress&mode=crop"),
    },
]


def get_news() -> list[dict]:
    """Return the news items, newest first."""
    return sorted(NEWS_ITEMS, key=lambda x: x["date"], reverse=True)


# --------------------------------------------------------------------------- #
#  6) SPORT-SPECIFIC CAREER STATISTICS                                         #
# --------------------------------------------------------------------------- #
# Each sport has its OWN performance metrics — cricket is runs/wickets, football
# is goals/assists, kabaddi is raid/tackle points, etc. Values are deterministic
# (seeded by athlete ID) and scaled by the athlete's tier anchor so stronger
# athletes read as stronger. Returns an ordered list of (label, value) pairs so
# the UI can render each sport's real stat card.

def generate_sport_stats(sport: str, event: str, aid: str, anchor: float,
                         matches: int) -> list[tuple[str, str]]:
    rng = _seed("sportstats-" + aid)
    q = (anchor - 55) / 44.0  # 0..~1 quality factor from tier anchor
    q = max(0.05, min(1.0, q))
    ev = (event or "").lower()

    def scaled(lo, hi):
        return int(lo + (hi - lo) * q * rng.uniform(0.8, 1.15))

    if sport == "Cricket":
        is_bowler = any(k in ev for k in ["bowl", "pace", "spin", "seam"])
        is_bat = any(k in ev for k in ["bat", "open", "top", "wicket", "keeper"])
        if not is_bowler and not is_bat:
            is_bat = is_bowler = True  # all-rounder
        runs = scaled(300, 6500) if is_bat else scaled(80, 1200)
        avg = round(rng.uniform(18, 32) + q * 18, 2)
        sr = round(rng.uniform(68, 92) + q * 45, 1)
        hundreds = scaled(0, 22) if is_bat else 0
        fifties = scaled(2, 40) if is_bat else scaled(0, 6)
        hs = scaled(35, 160) if is_bat else scaled(10, 55)
        wkts = scaled(20, 320) if is_bowler else scaled(0, 25)
        bowl_avg = round(rng.uniform(20, 34) - q * 6, 2) if is_bowler else 0
        econ = round(rng.uniform(3.6, 5.8) - q * 0.6, 2) if is_bowler else 0
        catches = scaled(5, 180)
        out = [("Matches", f"{matches}"), ("Runs", f"{runs:,}"),
               ("Batting Avg", f"{avg}"), ("Strike Rate", f"{sr}"),
               ("50s / 100s", f"{fifties} / {hundreds}"), ("High Score", f"{hs}")]
        if is_bowler:
            out += [("Wickets", f"{wkts}"), ("Bowling Avg", f"{bowl_avg}"),
                    ("Economy", f"{econ}")]
        out += [("Catches", f"{catches}")]
        return out

    if sport == "Football":
        is_gk = "keeper" in ev or "goalkeep" in ev or "gk" in ev
        is_def = any(k in ev for k in ["back", "def", "centre-b", "full-b"])
        is_fwd = any(k in ev for k in ["forward", "strik", "wing", "att"])
        apps = matches
        goals = scaled(0, 5) if is_gk else scaled(2, 90) if is_fwd else scaled(0, 30)
        assists = scaled(0, 3) if is_gk else scaled(2, 70)
        minutes = apps * rng.randint(55, 90)
        clean = scaled(2, 60) if (is_gk or is_def) else 0
        yellow = scaled(2, 45); red = scaled(0, 6)
        passpct = round(rng.uniform(68, 82) + q * 10, 1)
        out = [("Appearances", f"{apps}"), ("Goals", f"{goals}"),
               ("Assists", f"{assists}"), ("Minutes", f"{minutes:,}"),
               ("Pass %", f"{passpct}%"), ("Yellow / Red", f"{yellow} / {red}")]
        if is_gk or is_def:
            out.insert(4, ("Clean Sheets", f"{clean}"))
        return out

    if sport == "Chess":
        elo = int(1900 + q * 700 + rng.randint(-60, 60))
        peak = elo + rng.randint(20, 120)
        games = matches * rng.randint(3, 6)
        wins = int(games * (0.32 + q * 0.18))
        draws = int(games * rng.uniform(0.28, 0.4))
        losses = max(0, games - wins - draws)
        title = ("Grandmaster" if elo >= 2500 else "International Master" if elo >= 2400
                 else "FIDE Master" if elo >= 2300 else "Candidate Master" if elo >= 2200
                 else "Untitled")
        return [("FIDE Elo", f"{elo}"), ("Peak Elo", f"{peak}"), ("Title", title),
                ("Games", f"{games}"), ("W / D / L", f"{wins} / {draws} / {losses}"),
                ("Win rate", f"{round(wins/max(1,games)*100,1)}%"),
                ("Tournaments won", f"{scaled(0, 14)}")]

    if sport == "Athletics":
        golds = scaled(0, 12); silvers = scaled(0, 10); bronzes = scaled(0, 9)
        comps = matches + scaled(4, 30)
        pb = _athletics_pb(event, q, rng)
        return [("Event", event or "Track/Field"), ("Personal Best", pb),
                ("Competitions", f"{comps}"),
                ("Gold / Silver / Bronze", f"{golds} / {silvers} / {bronzes}"),
                ("Podium finishes", f"{golds+silvers+bronzes}"),
                ("National record", "Yes" if q > 0.85 and rng.random() < 0.4 else "No")]

    if sport == "Swimming":
        pb = f"{rng.randint(0,2)}:{rng.randint(0,59):02d}.{rng.randint(0,99):02d}"
        golds = scaled(0, 14); finals = scaled(2, 40)
        return [("Primary event", event or "Freestyle"),
                ("Personal Best", pb), ("Finals reached", f"{finals}"),
                ("Golds", f"{golds}"),
                ("National records", f"{scaled(0,6)}"),
                ("Relay caps", f"{scaled(3, 40)}")]

    if sport == "Volleyball":
        pts = scaled(120, 2600); spikes = scaled(80, 1500)
        blocks = scaled(30, 700); aces = scaled(20, 400)
        return [("Matches", f"{matches}"), ("Total points", f"{pts:,}"),
                ("Spikes", f"{spikes:,}"), ("Blocks", f"{blocks}"),
                ("Aces", f"{aces}"), ("Position", event or "All-round")]

    if sport in ("Badminton", "Table Tennis"):
        body = "BWF" if sport == "Badminton" else "ITTF"
        wins = int(matches * (0.4 + q * 0.35))
        titles = scaled(0, 18)
        best_rank = max(8, int(400 - q * 360 + rng.randint(-20, 20)))
        out = [("Matches", f"{matches}"), ("Wins", f"{wins}"),
               ("Win %", f"{round(wins/max(1,matches)*100,1)}%"),
               ("Titles", f"{titles}"),
               (f"Best {body} rank", f"#{best_rank}"),
               ("Event", event or "Singles")]
        if sport == "Kabaddi":
            pass
        return out

    if sport == "Kabaddi":
        raid = scaled(40, 900); tackle = scaled(30, 650)
        super_raids = scaled(1, 40); super_tackles = scaled(1, 45)
        raid_pct = round(rng.uniform(38, 52) + q * 12, 1)
        return [("Matches", f"{matches}"), ("Raid points", f"{raid}"),
                ("Tackle points", f"{tackle}"), ("Super raids", f"{super_raids}"),
                ("Super tackles", f"{super_tackles}"),
                ("Successful raid %", f"{raid_pct}%"), ("Position", event or "All-Rounder")]

    if sport == "Martial Arts":
        bouts = matches; wins = int(bouts * (0.45 + q * 0.35))
        ko = int(wins * rng.uniform(0.2, 0.5)); losses = bouts - wins
        golds = scaled(0, 12); silvers = scaled(0, 9); bronzes = scaled(0, 8)
        belt = rng.choice(["Black Belt 1st Dan", "Black Belt 2nd Dan",
                           "Black Belt 3rd Dan", "Red-Black Belt"])
        wclass = rng.choice(["-54 kg", "-58 kg", "-63 kg", "-68 kg", "-74 kg",
                             "-80 kg", "+80 kg"])
        return [("Discipline", event or "Karate"), ("Weight class", wclass),
                ("Bouts", f"{bouts}"), ("Wins (KO)", f"{wins} ({ko})"),
                ("Losses", f"{losses}"),
                ("Gold / Silver / Bronze", f"{golds} / {silvers} / {bronzes}"),
                ("Rank", belt)]

    # Fallback (should not happen for the 10 known sports).
    return [("Matches", f"{matches}")]


def _athletics_pb(event: str, q: float, rng: random.Random) -> str:
    ev = (event or "").lower()
    if "100" in ev or "sprint" in ev:
        return f"{round(10.0 + (1-q)*1.2 + rng.uniform(0,0.3), 2)} s"
    if "200" in ev:
        return f"{round(20.3 + (1-q)*2.0 + rng.uniform(0,0.4), 2)} s"
    if "400" in ev:
        return f"{round(45.0 + (1-q)*4.0 + rng.uniform(0,0.6), 2)} s"
    if "long" in ev or "jump" in ev:
        return f"{round(6.5 + q*1.8 + rng.uniform(0,0.2), 2)} m"
    if "javelin" in ev or "throw" in ev or "shot" in ev:
        return f"{round(55 + q*30 + rng.uniform(0,3), 2)} m"
    if "marathon" in ev or "5000" in ev or "10000" in ev or "distance" in ev:
        return f"{rng.randint(13,32)}:{rng.randint(0,59):02d} min"
    return f"{round(11.0 + (1-q)*1.5, 2)} s"


# --------------------------------------------------------------------------- #
#  7) RULE BOOK  (real governing bodies + official links; rules paraphrased)   #
# --------------------------------------------------------------------------- #
# Governing bodies and official rulebook URLs are real. Key-rule bullets are
# concise paraphrases in our own words (no copyrighted text reproduced), for
# orientation only — the official link is the authoritative source.

RULEBOOK = {
    "Cricket": {
        "body": "International Cricket Council (ICC) · Laws by MCC",
        "url": "https://www.lords.org/mcc/the-laws-of-cricket",
        "summary": "Bat-and-ball sport, 11 players per side, played as Test, ODI and T20 formats.",
        "rules": [
            "Two teams of 11; one side bats to score runs while the other bowls and fields.",
            "A batter can be dismissed by bowled, caught, LBW, run-out, stumped and more.",
            "An over is six legal deliveries; formats differ by overs (T20 = 20, ODI = 50).",
            "The side with the most runs wins; ties may go to a Super Over in limited-overs.",
        ],
    },
    "Football": {
        "body": "FIFA · Laws of the Game by IFAB",
        "url": "https://www.theifab.com/laws-of-the-game/",
        "summary": "11-a-side, two 45-minute halves; most goals wins.",
        "rules": [
            "Each team fields 11 players including a goalkeeper; matches are 2 × 45 minutes.",
            "Offside applies to attackers ahead of the ball and second-last defender when played.",
            "Fouls yield direct/indirect free kicks or penalties; cautions are yellow/red cards.",
            "Knockout ties level after full time may use extra time and penalty kicks.",
        ],
    },
    "Athletics": {
        "body": "World Athletics",
        "url": "https://worldathletics.org/about-iaaf/documents/book-of-rules",
        "summary": "Track and field events measured by time (races) or distance/height (field).",
        "rules": [
            "Track races are timed; false starts can lead to disqualification.",
            "Field events (jumps/throws) count the best legal distance or height.",
            "Athletes must stay in lane where required and pass batons within zones in relays.",
            "Records require ratified conditions (e.g., legal wind readings for sprints/jumps).",
        ],
    },
    "Chess": {
        "body": "FIDE — International Chess Federation",
        "url": "https://handbook.fide.com/chapter/E012023",
        "summary": "Two-player strategy game; checkmate the opponent's king to win.",
        "rules": [
            "Pieces move in defined ways; White moves first, then players alternate.",
            "Win by checkmate; draws occur by stalemate, repetition, 50-move rule or agreement.",
            "Touch-move applies: a touched piece must be moved if legal.",
            "Rated games use clocks; flag-fall loses unless the position forbids checkmate.",
        ],
    },
    "Swimming": {
        "body": "World Aquatics (formerly FINA)",
        "url": "https://www.worldaquatics.com/rules",
        "summary": "Timed races across freestyle, backstroke, breaststroke, butterfly and medley.",
        "rules": [
            "Each stroke has legal technique rules; violations bring disqualification.",
            "Swimmers must touch walls correctly on turns and finishes per stroke.",
            "One false start disqualifies under current rules at sanctioned meets.",
            "Relays require legal exchanges; early take-off disqualifies the team.",
        ],
    },
    "Volleyball": {
        "body": "FIVB — Fédération Internationale de Volleyball",
        "url": "https://www.fivb.com/volleyball/the-game/rules-of-the-game/",
        "summary": "Six players per side; rally scoring, sets to 25 (win by 2).",
        "rules": [
            "Teams of six; a side may touch the ball up to three times before returning it.",
            "Rally scoring: a point is won on every rally regardless of who served.",
            "Sets are played to 25 (win by 2); a deciding fifth set is to 15.",
            "Players rotate on winning serve; back-row attack and net-touch rules apply.",
        ],
    },
    "Badminton": {
        "body": "BWF — Badminton World Federation (Laws of Badminton)",
        "url": "https://corporate.bwfbadminton.com/statutes/",
        "summary": "Racket sport; best of three games to 21 points with rally scoring.",
        "rules": [
            "Best of three games; first side to 21 points wins a game (win by 2, cap at 30).",
            "Rally scoring: a point is scored on every rally; serve passes on each point won.",
            "Ends change after each game and at 11 points in the third game.",
            "Service must be below a fixed height with the shuttle hit below the waist.",
        ],
    },
    "Table Tennis": {
        "body": "ITTF — International Table Tennis Federation",
        "url": "https://www.ittf.com/handbook/",
        "summary": "Games to 11 points (win by 2); matches are best of an odd number of games.",
        "rules": [
            "A game is won at 11 points; at 10–10 play continues until one side leads by 2.",
            "Service alternates every two points (every point from 10–10).",
            "The serve must be tossed visibly and struck without hiding the ball.",
            "Matches are best of 5 or 7 games at most competitive levels.",
        ],
    },
    "Kabaddi": {
        "body": "International Kabaddi Federation (IKF)",
        "url": "https://kabaddiikf.com/",
        "summary": "Contact team sport; raiders score by tackling; defenders score by stopping raids.",
        "rules": [
            "Seven players per side on court; a raider enters the opposing half to score.",
            "The raider must chant 'kabaddi' continuously and return without being tackled.",
            "Raiders earn touch/bonus points; defenders earn points for a successful tackle.",
            "Out players are revived as the opposing side scores; most points wins.",
        ],
    },
    "Martial Arts": {
        "body": "WKF (Karate) · World Taekwondo · IJF (Judo)",
        "url": "https://www.wkf.net/structure-rules",
        "summary": "Combat disciplines scored on strikes/throws within weight categories.",
        "rules": [
            "Bouts are contested within defined weight categories and time limits.",
            "Karate (kumite) scores ippon/waza-ari/yuko for controlled legal techniques.",
            "Taekwondo scores points for legal kicks/punches to scoring zones (electronic sensors).",
            "Judo rewards throws (ippon/waza-ari) and controlled grappling/holds.",
        ],
    },
}


def get_rulebook(sport: str) -> dict | None:
    return RULEBOOK.get(sport)


# --------------------------------------------------------------------------- #
#  8) NOTUN KURI — grassroots talent pipeline (illustrative demo data)         #
# --------------------------------------------------------------------------- #
# Modeled on REAL published figures for the Ministry of Youth & Sports'
# "Notun Kuri Sports" nationwide talent hunt (ages 12–14, 8 disciplines):
#   • 160,779 registered online (116,646 boys / 44,133 girls) in the first window
#   • Pathway: ward/union → upazila teams → divisional qualifiers → national pool
# All per-division / per-stage breakdowns below are ILLUSTRATIVE demonstration
# data consistent with those public totals — not official records.

NOTUN_KURI_TOTALS = {
    "registered": 160779,
    "boys": 116646,
    "girls": 44133,
    "disciplines": 10,
    "age_band": "12–14 years",
    "source_note": "National totals modeled on Ministry of Youth & Sports public "
                   "figures (registration window Apr 2026). Discipline and "
                   "division breakdowns are illustrative.",
}

# Disciplines aligned to the full platform (the programme's core 8 plus the two
# additional tracked sports, for pipeline continuity with the senior system).
NOTUN_KURI_SPORTS = ["Football", "Cricket", "Athletics", "Chess", "Badminton",
                     "Kabaddi", "Martial Arts", "Swimming", "Volleyball",
                     "Table Tennis"]


def get_notun_kuri():
    """Return illustrative Notun Kuri pipeline data derived from real totals."""
    import numpy as np
    reg = NOTUN_KURI_TOTALS["registered"]

    # --- Funnel stages (proportions are illustrative but plausible) ---
    stages = [
        ("Registered (online)", reg),
        ("Upazila teams formed", int(reg * 0.34)),
        ("Divisional qualifiers", int(reg * 0.11)),
        ("National talent pool", int(reg * 0.028)),
        ("Elite pathway / BKSP", int(reg * 0.006)),
    ]

    # --- By division (weighted by rough population share; sums to registered) ---
    div_weights = {
        "Dhaka": 0.26, "Chattogram": 0.19, "Rajshahi": 0.13, "Khulna": 0.11,
        "Rangpur": 0.10, "Sylhet": 0.08, "Barishal": 0.07, "Mymensingh": 0.06,
    }
    by_division = []
    running = 0
    items = list(div_weights.items())
    for i, (d, w) in enumerate(items):
        v = reg - running if i == len(items) - 1 else int(reg * w)
        running += v
        by_division.append({"division": d, "registered": v,
                            "boys": int(v * 0.725), "girls": v - int(v * 0.725)})

    # --- By discipline (footfall skewed to football/cricket) ---
    disc_weights = {"Football": 0.20, "Cricket": 0.18, "Athletics": 0.13,
                    "Kabaddi": 0.10, "Badminton": 0.09, "Chess": 0.08,
                    "Martial Arts": 0.06, "Swimming": 0.06, "Volleyball": 0.055,
                    "Table Tennis": 0.045}
    by_discipline = []
    running = 0
    ditems = list(disc_weights.items())
    for i, (s, w) in enumerate(ditems):
        v = reg - running if i == len(ditems) - 1 else int(reg * w)
        running += v
        by_discipline.append({"sport": s, "participants": v})

    return {
        "totals": NOTUN_KURI_TOTALS,
        "stages": stages,
        "by_division": by_division,
        "by_discipline": by_discipline,
    }
