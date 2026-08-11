# -*- coding: utf-8 -*-
"""
i18n.py
=======
Bilingual (English / বাংলা) support for the Sports Ministry dashboard.

WHAT IS TRANSLATED
-------------------
  • All navigation, page titles, section headers, KPI labels, filter labels,
    table column headers, status labels, button text, chart titles.
  • Fixed/enumerable generated-text pools in dataset.py (injury notes, recent-
    stat templates, coach feedback, achievements, certificates, specialisations)
    via GENERATED_TEXT_BN below.
  • Rule Book summaries and News Center headlines/summaries (RULEBOOK_BN,
    NEWS_BN) — these are fixed dictionaries, safe to translate fully.
  • The AI recommendation engine (dataset.generate_recommendations) takes a
    lang parameter and branches each message template in Bangla directly —
    see dataset.py.

WHAT IS DELIBERATELY KEPT IN ENGLISH
-------------------------------------
  • Real people's names (players, coaches) — accurate transliteration into
    Bangla script for hundreds of names is error-prone; matches common
    practice on official Bangladeshi digital platforms.
  • Numerals stay Arabic (0-9), not Bengali (০-৯) — matches how virtually
    every official BD government dashboard displays statistics.

USAGE
-----
    from i18n import t, LANG_KEY
    st.session_state.setdefault(LANG_KEY, "en")
    ...
    st.markdown(t("nav_glance"))
"""

from __future__ import annotations

import streamlit as st

LANG_KEY = "app_lang"   # "en" or "bn"

# --------------------------------------------------------------------------- #
#  FONT — Bangla script requires a font that actually renders it. None of the
#  dashboard's existing fonts (Inter, Plus Jakarta Sans) support Bengali
#  glyphs, so unsupported characters would render as empty boxes without this.
# --------------------------------------------------------------------------- #
BANGLA_FONT_CSS = """
/* Deliberately empty: an earlier version of this file force-applied a custom
   Bangla webfont across the whole app (.stApp), which broke the sidebar --
   Noto Sans Bengali also ships full Latin/numeral glyph coverage (standard
   for Noto-family fonts), so it silently overrode English text, numbers,
   and icon-ligature elements throughout the sidebar (collapse arrow,
   expander chevrons, weight-slider labels), not just Bengali text.
   Every mainstream browser/OS already ships a Bengali-capable system font
   and falls back to it automatically for any glyph the primary font stack
   doesn't cover -- so Bangla text still renders correctly (never as empty
   'tofu' boxes) without this override. This trades a perfectly-matched
   custom Bengali typeface for guaranteed zero risk to the rest of the UI,
   which is the right trade this close to a live demonstration. If a
   branded Bengali webfont is wanted later, it must be applied narrowly
   (e.g. a dedicated .bn-text class wrapped around specific translated
   strings at the point of use) -- never as a blanket .stApp rule. */
"""




def current_lang() -> str:
    return st.session_state.get(LANG_KEY, "en")


def is_bangla() -> bool:
    return current_lang() == "bn"


def t(key: str, **kwargs) -> str:
    """Look up a UI string in the current language. Falls back to English,
    then to the key itself, so a missing translation never crashes the app."""
    entry = UI.get(key)
    if entry is None:
        return key
    text = entry.get(current_lang(), entry.get("en", key))
    return text.format(**kwargs) if kwargs else text


def gt(english_text: str) -> str:
    """Look up a known GENERATED text string (from dataset.py's enumerable
    pools) and return its Bangla equivalent if we're in Bangla mode and a
    translation exists; otherwise returns the original English unchanged."""
    if not is_bangla():
        return english_text
    return GENERATED_TEXT_BN.get(english_text, english_text)


_STATUS_KEY_MAP = {
    "Fully Fit": "status_fully_fit",
    "Cleared / Recovered": "status_cleared",
    "Actively Managed": "status_managed",
    "Monitored / Restricted": "status_restricted",
}


def ts(status_text: str) -> str:
    """Translate an injury-status label (Fully Fit / Cleared / Actively
    Managed / Monitored-Restricted) to Bangla when active."""
    key = _STATUS_KEY_MAP.get(status_text)
    return t(key) if key else status_text


# --------------------------------------------------------------------------- #
#  UI STRING TABLE                                                             #
# --------------------------------------------------------------------------- #
UI: dict[str, dict[str, str]] = {
    # ---- Sidebar / brand ----
    "brand_title": {"en": "Sports Ministry", "bn": "ক্রীড়া মন্ত্রণালয়"},
    "brand_sub": {"en": "National Performance Portal", "bn": "জাতীয় পারফরম্যান্স পোর্টাল"},
    "nav_label": {"en": "Navigation", "bn": "নেভিগেশন"},
    "filters_label": {"en": "Filters", "bn": "ফিল্টার"},
    "language_label": {"en": "🌐 Language", "bn": "🌐 ভাষা"},

    # ---- Nav items ----
    "nav_glance": {"en": "At a Glance", "bn": "এক নজরে"},
    "nav_notunkuri": {"en": "Notun Kuri", "bn": "নতুন কুঁড়ি"},
    "nav_stipend": {"en": "Stipend Program", "bn": "উপবৃত্তি কর্মসূচি"},
    "nav_summary": {"en": "Executive Summary", "bn": "নির্বাহী সারসংক্ষেপ"},
    "nav_profile": {"en": "Player Profile", "bn": "খেলোয়াড় প্রোফাইল"},
    "nav_fitness": {"en": "Performance & Fitness", "bn": "পারফরম্যান্স ও ফিটনেস"},
    "nav_injury": {"en": "Injury & Training", "bn": "ইনজুরি ও প্রশিক্ষণ"},
    "nav_rankings": {"en": "Rankings & Leaderboard", "bn": "র‍্যাঙ্কিং ও লিডারবোর্ড"},
    "nav_coaches": {"en": "Coach Directory", "bn": "কোচ ডিরেক্টরি"},
    "nav_rules": {"en": "Rule Book", "bn": "নিয়মাবলী"},
    "nav_news": {"en": "News Center", "bn": "সংবাদ কেন্দ্র"},

    # ---- Filters ----
    "filter_sport": {"en": "🏆 Sport", "bn": "🏆 খেলা"},
    "filter_all_sports": {"en": "All Sports", "bn": "সকল খেলা"},
    "filter_search": {"en": "🔍 Smart search", "bn": "🔍 স্মার্ট সার্চ"},
    "filter_search_placeholder": {"en": "name, club, district, event…",
                                  "bn": "নাম, ক্লাব, জেলা, ইভেন্ট…"},
    "filter_advanced": {"en": "🔎 Advanced filters", "bn": "🔎 উন্নত ফিল্টার"},
    "filter_division": {"en": "Division", "bn": "বিভাগ"},
    "filter_district": {"en": "District", "bn": "জেলা"},
    "filter_gender": {"en": "Gender", "bn": "লিঙ্গ"},
    "filter_availability": {"en": "Availability", "bn": "প্রাপ্যতা"},
    "filter_club": {"en": "Club", "bn": "ক্লাব"},
    "filter_national_team": {"en": "National team", "bn": "জাতীয় দল"},
    "filter_age": {"en": "Age", "bn": "বয়স"},
    "filter_performance": {"en": "Performance rating", "bn": "পারফরম্যান্স রেটিং"},
    "filter_fitness": {"en": "Fitness rating", "bn": "ফিটনেস রেটিং"},
    "filter_career_win": {"en": "Career win %", "bn": "ক্যারিয়ার জয়ের হার %"},
    "filter_clear": {"en": "↺ Clear filters", "bn": "↺ ফিল্টার মুছুন"},
    "filter_player": {"en": "👤 Player", "bn": "👤 খেলোয়াড়"},
    "filter_scope_caption": {"en": "{n} of {total} athlete(s) in scope",
                             "bn": "{total} জনের মধ্যে {n} জন অ্যাথলিট নির্বাচিত"},

    # ---- Common section/table words ----
    "col_name": {"en": "Name", "bn": "নাম"},
    "col_sport": {"en": "Sport", "bn": "খেলা"},
    "col_division": {"en": "Division", "bn": "বিভাগ"},
    "col_tier": {"en": "Tier", "bn": "স্তর"},
    "col_overall": {"en": "Overall", "bn": "সার্বিক স্কোর"},
    "col_percentile": {"en": "Percentile", "bn": "পার্সেন্টাইল"},
    "col_status": {"en": "Status", "bn": "অবস্থা"},
    "col_rank": {"en": "Rank", "bn": "র‍্যাঙ্ক"},
    "download_csv": {"en": "⬇️ Download this leaderboard (CSV)",
                     "bn": "⬇️ লিডারবোর্ড ডাউনলোড করুন (CSV)"},

    # ---- Injury statuses ----
    "status_fully_fit": {"en": "Fully Fit", "bn": "সম্পূর্ণ ফিট"},
    "status_cleared": {"en": "Cleared / Recovered", "bn": "সেরে উঠেছে"},
    "status_managed": {"en": "Actively Managed", "bn": "পর্যবেক্ষণে আছে"},
    "status_restricted": {"en": "Monitored / Restricted", "bn": "সীমাবদ্ধ / পর্যবেক্ষণে"},

    # ---- Executive Summary ----
    "page_summary_title": {"en": "Executive briefing — national programme",
                           "bn": "নির্বাহী প্রতিবেদন — জাতীয় কর্মসূচি"},
    "page_summary_sub": {"en": "A single-page synthesis of the whole system: "
                         "grassroots pipeline, elite pool, performance, coverage and readiness.",
                         "bn": "সম্পূর্ণ ব্যবস্থার এক-পৃষ্ঠার সারসংক্ষেপ: তৃণমূল পাইপলাইন, "
                         "এলিট পুল, পারফরম্যান্স, কভারেজ এবং প্রস্তুতি।"},
    "kpi_grassroots": {"en": "Grassroots pipeline", "bn": "তৃণমূল পাইপলাইন"},
    "kpi_registered": {"en": "Notun Kuri registered", "bn": "নতুন কুঁড়ি নিবন্ধিত"},
    "kpi_elite": {"en": "Elite athletes", "bn": "এলিট অ্যাথলিট"},
    "kpi_coaches": {"en": "Coaches & staff", "bn": "কোচ ও স্টাফ"},
    "kpi_avg_perf": {"en": "Avg performance", "bn": "গড় পারফরম্যান্স"},
    "kpi_model_score": {"en": "0–100 model score", "bn": "০–১০০ মডেল স্কোর"},
    "kpi_match_ready": {"en": "Match-ready", "bn": "খেলার জন্য প্রস্তুত"},
    "kpi_on_watch": {"en": "on injury watch", "bn": "ইনজুরি পর্যবেক্ষণে"},
    "sec_pipeline": {"en": "Talent pipeline — grassroots to elite",
                     "bn": "প্রতিভা পাইপলাইন — তৃণমূল থেকে এলিট"},
    "sec_top_performers": {"en": "Top performers nationwide", "bn": "দেশজুড়ে শীর্ষ পারফরমার"},
    "sec_by_sport": {"en": "Elite athletes by sport", "bn": "খেলাভিত্তিক এলিট অ্যাথলিট"},
    "sec_readiness": {"en": "Squad readiness", "bn": "দলের প্রস্তুতি"},
    "sec_insights": {"en": "Key insights", "bn": "মূল পর্যবেক্ষণ"},

    # ---- Player Profile ----
    "tab_overview": {"en": "📋 Overview", "bn": "📋 সারসংক্ষেপ"},
    "tab_personal": {"en": "👤 Personal", "bn": "👤 ব্যক্তিগত"},
    "tab_career": {"en": "🏆 Career", "bn": "🏆 ক্যারিয়ার"},
    "tab_performance": {"en": "📈 Performance", "bn": "📈 পারফরম্যান্স"},
    "tab_fitness_training": {"en": "💪 Fitness & Training", "bn": "💪 ফিটনেস ও প্রশিক্ষণ"},
    "tab_health_coach": {"en": "🩺 Health & Coach", "bn": "🩺 স্বাস্থ্য ও কোচ"},
    "tab_ai_insights": {"en": "🤖 AI Insights", "bn": "🤖 এআই পরামর্শ"},
    "tab_compare": {"en": "⚖️ Compare", "bn": "⚖️ তুলনা"},
    "tab_export": {"en": "⬇️ Export", "bn": "⬇️ এক্সপোর্ট"},
    "sec_biometrics": {"en": "Biometrics & vitals", "bn": "শারীরিক পরিমাপ ও গুরুত্বপূর্ণ তথ্য"},
    "sec_component_breakdown": {"en": "Component breakdown (0–100, vs same-sport peers)",
                                "bn": "উপাদান বিশ্লেষণ (০–১০০, একই খেলার সমকক্ষদের তুলনায়)"},
    "metric_age": {"en": "Age", "bn": "বয়স"},
    "metric_height": {"en": "Height", "bn": "উচ্চতা"},
    "metric_weight": {"en": "Weight", "bn": "ওজন"},
    "metric_vo2": {"en": "VO₂ Max", "bn": "VO₂ ম্যাক্স"},
    "metric_resting_hr": {"en": "Resting HR", "bn": "বিশ্রামকালীন হৃদস্পন্দন"},
    "metric_body_fat": {"en": "Body Fat", "bn": "শরীরের চর্বি"},
    "metric_intake": {"en": "Daily Intake", "bn": "দৈনিক ক্যালরি গ্রহণ"},
    "metric_burn": {"en": "Daily Burn", "bn": "দৈনিক ক্যালরি খরচ"},
    "metric_energy_balance": {"en": "Energy Balance", "bn": "শক্তির ভারসাম্য"},
    "metric_injury_status": {"en": "Injury status", "bn": "ইনজুরি অবস্থা"},

    # ---- Coach Directory ----
    "page_coaches_title": {"en": "Coach Directory", "bn": "কোচ ডিরেক্টরি"},
    "coach_search": {"en": "🔍 Coach search", "bn": "🔍 কোচ অনুসন্ধান"},
    "coach_verified": {"en": "✓ VERIFIED", "bn": "✓ যাচাইকৃত"},
    "coach_illustrative": {"en": "ILLUSTRATIVE", "bn": "উদাহরণস্বরূপ"},

    # ---- Rule Book ----
    "page_rules_title": {"en": "Sport Rule Books", "bn": "খেলার নিয়মাবলী"},
    "choose_sport": {"en": "Choose a sport", "bn": "একটি খেলা বেছে নিন"},
    "key_rules": {"en": "Key rules", "bn": "মূল নিয়মসমূহ"},
    "open_official": {"en": "📘 Open the official {sport} rulebook",
                      "bn": "📘 {sport} এর সরকারি নিয়মাবলী দেখুন"},

    # ---- News Center ----
    "page_news_title": {"en": "Sports News Center", "bn": "ক্রীড়া সংবাদ কেন্দ্র"},
    "filter_category": {"en": "Filter by category", "bn": "বিভাগ অনুযায়ী ফিল্টার"},
    "filter_priority": {"en": "Filter by priority", "bn": "অগ্রাধিকার অনুযায়ী ফিল্টার"},

    # ---- Notun Kuri ----
    "page_notunkuri_title": {"en": "Notun Kuri — National Talent Pipeline",
                             "bn": "নতুন কুঁড়ি — জাতীয় প্রতিভা পাইপলাইন"},
    "sec_funnel": {"en": "Talent pathway funnel", "bn": "প্রতিভা অনুসন্ধান ধাপসমূহ"},
    "sec_gender_participation": {"en": "Participation by gender", "bn": "লিঙ্গভিত্তিক অংশগ্রহণ"},
    "sec_by_discipline": {"en": "Registrations by discipline", "bn": "বিষয়ভিত্তিক নিবন্ধন"},
    "sec_reach_map": {"en": "Grassroots reach across Bangladesh",
                      "bn": "সারা বাংলাদেশে তৃণমূল সম্প্রসারণ"},

    # ---- Stipend Program ----
    "page_stipend_title": {"en": "Notun Kuri Stipend Program",
                           "bn": "নতুন কুঁড়ি উপবৃত্তি কর্মসূচি"},
    "page_stipend_sub": {"en": "Monthly development allowance · Top 400 selected stars · "
                         "Ministry of Youth & Sports",
                         "bn": "মাসিক উন্নয়ন ভাতা · শীর্ষ নির্বাচিত ৪০০ তারকা · "
                         "যুব ও ক্রীড়া মন্ত্রণালয়"},
    "kpi_selected_stars": {"en": "Selected stars", "bn": "নির্বাচিত তারকা"},
    "kpi_active_month": {"en": "Active this month", "bn": "এই মাসে সক্রিয়"},
    "kpi_disbursed_month": {"en": "Disbursed this month", "bn": "এই মাসে বিতরণকৃত"},
    "kpi_disbursed_total": {"en": "Total disbursed (all-time)", "bn": "মোট বিতরণকৃত (সর্বমোট)"},
    "kpi_paid_month": {"en": "Paid this month", "bn": "এই মাসে পরিশোধিত"},
    "kpi_pending": {"en": "Pending", "bn": "মুলতুবি"},
    "kpi_failed": {"en": "Failed", "bn": "ব্যর্থ"},
    "kpi_on_hold": {"en": "On hold", "bn": "স্থগিত"},
    "sec_disbursement_trend": {"en": "Monthly disbursement trend", "bn": "মাসিক বিতরণের প্রবণতা"},
    "sec_month_status": {"en": "This month's status", "bn": "এই মাসের অবস্থা"},
    "sec_stars_by_division": {"en": "Stars by division", "bn": "বিভাগভিত্তিক তারকা"},
    "sec_stars_by_method": {"en": "Stars by disbursement method",
                            "bn": "বিতরণ পদ্ধতি অনুযায়ী তারকা"},
    "sec_payment_register": {"en": "Payment register — this month",
                             "bn": "অর্থপ্রদান নিবন্ধন — এই মাস"},
    "sec_process_payment": {"en": "Process payment (demonstration workflow)",
                            "bn": "অর্থপ্রদান প্রক্রিয়া (প্রদর্শনী কর্মপ্রবাহ)"},
    "search_star": {"en": "🔍 Search star", "bn": "🔍 তারকা অনুসন্ধান"},
    "simulate_disbursement": {"en": "🔒 Simulate disbursement — ৳{amount}",
                              "bn": "🔒 বিতরণ অনুকরণ করুন — ৳{amount}"},
    "status_paid": {"en": "Paid", "bn": "পরিশোধিত"},
    "status_pending": {"en": "Pending", "bn": "মুলতুবি"},
    "status_failed": {"en": "Failed", "bn": "ব্যর্থ"},
    "status_held": {"en": "Held", "bn": "স্থগিত"},

    # ---- Rankings ----
    "page_rankings_title": {"en": "Within-sport ranking model", "bn": "খেলাভিত্তিক র‍্যাঙ্কিং মডেল"},
    "sec_ranking_formula": {"en": "📐 How the overall score is calculated",
                            "bn": "📐 সার্বিক স্কোর কীভাবে হিসাব করা হয়"},

    # ---- Kitchen / injury page reused labels ----
    "sec_availability_breakdown": {"en": "Availability breakdown", "bn": "প্রাপ্যতার বিশ্লেষণ"},
    "sec_training_load": {"en": "Training load vs availability",
                          "bn": "প্রশিক্ষণ লোড বনাম প্রাপ্যতা"},
    "sec_calorie": {"en": "Calorie intake vs burn", "bn": "ক্যালরি গ্রহণ বনাম খরচ"},

    # ---- Misc common ----
    "footer_note": {"en": "Demonstration build · Data read directly from the source "
                    "workbook (unmodified). Scores are model-derived from the supplied "
                    "fields; no values were fabricated.",
                    "bn": "প্রদর্শনী সংস্করণ · উৎস তথ্য থেকে সরাসরি পঠিত (অপরিবর্তিত)। "
                    "স্কোর প্রদত্ত তথ্যের ভিত্তিতে মডেল দ্বারা নির্ধারিত; কোনো মান বানানো হয়নি।"},

    # ---- Performance & Fitness / Injury & Training KPIs ----
    "kpi_fully_fit": {"en": "Fully Fit", "bn": "সম্পূর্ণ ফিট"},
    "kpi_on_watch_full": {"en": "On Injury Watch", "bn": "ইনজুরি পর্যবেক্ষণে"},
    "kpi_avg_burn": {"en": "Avg Training Burn", "bn": "গড় প্রশিক্ষণ ক্যালরি খরচ"},
    "kpi_avg_avail": {"en": "Avg Availability", "bn": "গড় প্রাপ্যতা"},
    "foot_of_scope": {"en": "% of scope", "bn": "% নির্বাচিত পরিসরের"},
    "foot_managed_restricted": {"en": "managed or restricted", "bn": "পরিচালিত বা সীমাবদ্ধ"},
    "foot_kcal_day": {"en": "kcal / day", "bn": "ক্যালরি / দিন"},
    "foot_health_index": {"en": "health index (0–100)", "bn": "স্বাস্থ্য সূচক (০–১০০)"},

    # ---- Rankings page ----
    "kpi_avg_overall": {"en": "Avg Overall Score", "bn": "গড় সার্বিক স্কোর"},
    "kpi_top_score": {"en": "Top Score", "bn": "সর্বোচ্চ স্কোর"},
    "kpi_athletes_scope": {"en": "Athletes in Scope", "bn": "নির্বাচিত অ্যাথলিট"},
    "kpi_sports_covered": {"en": "Sports Covered", "bn": "অন্তর্ভুক্ত খেলা"},

    # ---- Coach Directory ----
    "coach_search_placeholder": {"en": "name or division…", "bn": "নাম বা বিভাগ…"},
    "kpi_total_coaches": {"en": "Total Coaches", "bn": "মোট কোচ"},
    "kpi_national_coaches": {"en": "National Level", "bn": "জাতীয় পর্যায়ে"},
    "kpi_avg_experience": {"en": "Avg Experience", "bn": "গড় অভিজ্ঞতা"},
    "kpi_avg_rating": {"en": "Avg Rating", "bn": "গড় রেটিং"},

    # ---- Notun Kuri KPIs ----
    "kpi_total_registered": {"en": "Total Registered", "bn": "মোট নিবন্ধিত"},
    "kpi_boys": {"en": "Boys", "bn": "ছেলে"},
    "kpi_girls": {"en": "Girls", "bn": "মেয়ে"},
    "kpi_disciplines": {"en": "Disciplines", "bn": "বিষয়"},

    # ---- Performance & Fitness ----
    "sec_fitness_analytics": {"en": "Fitness analytics — {scope}", "bn": "ফিটনেস বিশ্লেষণ — {scope}"},
    "scope_all_sports": {"en": "all sports", "bn": "সকল খেলা"},
    "kpi_avg_vo2": {"en": "Avg VO₂ Max", "bn": "গড় VO₂ ম্যাক্স"},
    "kpi_avg_resting_hr": {"en": "Avg Resting HR", "bn": "গড় বিশ্রামকালীন হৃদস্পন্দন"},
    "kpi_avg_bodyfat": {"en": "Avg Body Fat", "bn": "গড় শরীরের চর্বি"},
    "kpi_fittest": {"en": "Fittest (overall)", "bn": "সবচেয়ে ফিট (সার্বিক)"},
    "foot_fitness_index": {"en": "fitness index {v}", "bn": "ফিটনেস সূচক {v}"},
    "foot_current_weight": {"en": "current weight", "bn": "বর্তমান ওজন"},
    "exp_how_calculated": {"en": "📐 How the overall score is calculated",
                           "bn": "📐 সার্বিক স্কোর কীভাবে হিসাব করা হয়"},
    "info_top_of_sport": {"en": "Showing the **top athlete of every sport**. "
                          "Pick a sport in the sidebar for its full leaderboard.",
                          "bn": "**প্রতিটি খেলার শীর্ষ অ্যাথলিট** দেখানো হচ্ছে। "
                          "সম্পূর্ণ লিডারবোর্ডের জন্য সাইডবারে একটি খেলা নির্বাচন করুন।"},
    "sport_leaders": {"en": "Sport leaders", "bn": "খেলাভিত্তিক শীর্ষস্থানীয়"},
}


# --------------------------------------------------------------------------- #
#  GENERATED TEXT TRANSLATIONS                                                 #
#  Bangla equivalents for dataset.py's finite, enumerable generated-text pools.
#  Looked up via gt(english_string) at display time — the underlying English
#  data generation in dataset.py is completely untouched, so nothing about
#  scoring, filtering, or data generation changes; only what's SHOWN changes.
# --------------------------------------------------------------------------- #
GENERATED_TEXT_BN: dict[str, str] = {
    # ---- Injury history templates (generate_new_sport_rows) ----
    "Clear medical log; premium fitness.":
        "পরিষ্কার চিকিৎসা রেকর্ড; উত্তম ফিটনেস।",
    "Managed minor ankle sprain; fully recovered.":
        "সামান্য গোড়ালি মচকানো নিয়ন্ত্রণে; সম্পূর্ণ সুস্থ।",
    "Routine load monitoring; no restrictions.":
        "নিয়মিত লোড পর্যবেক্ষণ; কোনো সীমাবদ্ধতা নেই।",
    "Recovered shoulder strain (2024); 100% cleared.":
        "কাঁধের আঘাত থেকে সুস্থ (২০২৪); ১০০% ছাড়পত্র প্রাপ্ত।",
    "Under preventive knee-management programme.":
        "প্রতিরোধমূলক হাঁটু-ব্যবস্থাপনা কর্মসূচির আওতায়।",
    "No historic major injuries recorded.":
        "কোনো বড় ইনজুরির পূর্ব রেকর্ড নেই।",

    # ---- _recent_stat templates ----
    "Reached national semi-final; strong smash accuracy.":
        "জাতীয় সেমিফাইনালে পৌঁছেছে; শক্তিশালী স্ম্যাশ নির্ভুলতা।",
    "Divisional champion; consistent rally control.":
        "বিভাগীয় চ্যাম্পিয়ন; ধারাবাহিক র‍্যালি নিয়ন্ত্রণ।",
    "National doubles medallist; sharp net play.":
        "জাতীয় ডাবলসে পদকজয়ী; তীক্ষ্ণ নেট খেলা।",
    "Federation Cup quarter-finalist; fast topspin game.":
        "ফেডারেশন কাপ কোয়ার্টার-ফাইনালিস্ট; দ্রুত টপস্পিন খেলা।",
    "National ranking climber; solid backhand block.":
        "জাতীয় র‍্যাঙ্কিংয়ে উন্নতিশীল; দৃঢ় ব্যাকহ্যান্ড ব্লক।",
    "Divisional singles medallist; quick footwork.":
        "বিভাগীয় সিঙ্গেলসে পদকজয়ী; দ্রুত ফুটওয়ার্ক।",
    "High raid-success rate in national league.":
        "জাতীয় লিগে উচ্চ রেইড-সাফল্যের হার।",
    "Key defender; multiple super-tackles this season.":
        "মূল ডিফেন্ডার; এই মৌসুমে একাধিক সুপার-ট্যাকল।",
    "All-rounder; strong bonus-point conversion.":
        "অলরাউন্ডার; শক্তিশালী বোনাস-পয়েন্ট রূপান্তর।",
    "National kumite medallist; disciplined guard.":
        "জাতীয় কুমিতেতে পদকজয়ী; সুশৃঙ্খল গার্ড।",
    "Divisional gold; strong poomsae precision.":
        "বিভাগীয় স্বর্ণপদক; নিখুঁত পুমসে নির্ভুলতা।",
    "Consistent podium finisher in weight class.":
        "নিজ ওজন শ্রেণীতে ধারাবাহিক পোডিয়াম ফিনিশার।",

    # ---- Coach feedback templates (_coach_feedback) ----
    ("Managing workload carefully this cycle; technically sound, and I "
     "expect a strong return once fully cleared."):
        "এই চক্রে সতর্কতার সাথে কর্মভার সামলাচ্ছে; কৌশলগতভাবে দক্ষ, "
        "সম্পূর্ণ সুস্থ হলে শক্তিশালী প্রত্যাবর্তন আশা করছি।",
    ("A standout in the divisional pool — disciplined in training and "
     "reliable under pressure. Pushing for national-camp selection."):
        "বিভাগীয় পুলে অসাধারণ — প্রশিক্ষণে সুশৃঙ্খল এবং চাপের মধ্যে নির্ভরযোগ্য। "
        "জাতীয় ক্যাম্পে নির্বাচনের জন্য চেষ্টা করছি।",
    ("Solid, coachable athlete with clear upside. Consistency in the "
     "gym is turning into competition results."):
        "দৃঢ়, প্রশিক্ষণযোগ্য অ্যাথলিট যার সম্ভাবনা স্পষ্ট। জিমে ধারাবাহিকতা "
        "প্রতিযোগিতার ফলাফলে রূপান্তরিত হচ্ছে।",
    ("Raw potential that needs volume and routine. With steady attendance "
     "the base will come quickly."):
        "অপরিশোধিত সম্ভাবনা যার জন্য পরিমাণ ও রুটিন প্রয়োজন। নিয়মিত উপস্থিতিতে "
        "ভিত্তি দ্রুত তৈরি হবে।",

    # ---- Coach certificate pool ----
    "High-Performance Coaching": "উচ্চ-পারফরম্যান্স কোচিং",
    "Sports Nutrition L3": "স্পোর্টস নিউট্রিশন লেভেল ৩",
    "Advanced S&C": "উন্নত শক্তি ও কন্ডিশনিং",
    "Anti-Doping (WADA)": "ডোপিং-বিরোধী (WADA)",
    "Talent ID Certified": "প্রতিভা শনাক্তকরণ সনদপ্রাপ্ত",
    "NSC Advanced Coaching": "এনএসসি উন্নত কোচিং",
    "Sports Nutrition Level 2": "স্পোর্টস নিউট্রিশন লেভেল ২",
    "Strength & Conditioning Cert.": "শক্তি ও কন্ডিশনিং সনদ",
    "Anti-Doping (WADA) Certified": "ডোপিং-বিরোধী (WADA) সনদপ্রাপ্ত",
    "Sports Psychology Workshop": "স্পোর্টস সাইকোলজি কর্মশালা",
    "First-Aid & Rehab Certified": "প্রাথমিক চিকিৎসা ও পুনর্বাসন সনদপ্রাপ্ত",

    # ---- Coach achievements pool ----
    "National-team head/assistant role": "জাতীয় দলের প্রধান/সহকারী দায়িত্ব",
    "Guided athletes to SA Games podium": "অ্যাথলেটদের সাফ গেমসের পোডিয়ামে পৌঁছে দিয়েছেন",
    "Built national development pipeline": "জাতীয় উন্নয়ন পাইপলাইন গড়ে তুলেছেন",
    "International tournament experience": "আন্তর্জাতিক টুর্নামেন্টের অভিজ্ঞতা",
    "Produced 3+ national medallists": "৩+ জাতীয় পদকজয়ী তৈরি করেছেন",
    "Divisional Coach of the Year": "বছরের সেরা বিভাগীয় কোচ",
    "Led team to National Games podium": "দলকে জাতীয় গেমসের পোডিয়ামে পৌঁছে দিয়েছেন",
    "Developed youth pipeline": "যুব পাইপলাইন গড়ে তুলেছেন",
    "SA Games support-staff experience": "সাফ গেমসে সহায়ক-স্টাফ হিসেবে অভিজ্ঞতা",
    "20+ athletes to national camp": "২০+ অ্যাথলেটকে জাতীয় ক্যাম্পে পাঠিয়েছেন",

    # ---- Coach specialisation pool (_coach_spec) ----
    "Technique & fundamentals": "কৌশল ও মূলনীতি",
    "Strength & conditioning": "শক্তি ও কন্ডিশনিং",
    "Youth development": "যুব উন্নয়ন",
    "High-performance / elite prep": "উচ্চ-পারফরম্যান্স / এলিট প্রস্তুতি",
    "Tactical analysis": "কৌশলগত বিশ্লেষণ",
    "Rehabilitation & load management": "পুনর্বাসন ও লোড ব্যবস্থাপনা",

    # ---- AI recommendation component labels ----
    "Fitness": "ফিটনেস", "Career": "ক্যারিয়ার", "Nutrition": "পুষ্টি",
    "Attendance": "উপস্থিতি", "Availability": "প্রাপ্যতা", "Coach eval": "কোচ মূল্যায়ন",

    # ---- Career highlights pool (enrich_profiles) ----
    "National title holder": "জাতীয় শিরোপাধারী",
    "Represented Bangladesh internationally": "আন্তর্জাতিক পর্যায়ে বাংলাদেশের প্রতিনিধিত্ব করেছেন",
    "Divisional record holder": "বিভাগীয় রেকর্ডধারী",
    "Youngest medallist in category": "নিজ বিভাগে সর্বকনিষ্ঠ পদকজয়ী",
    "Multiple-season top performer": "একাধিক মৌসুমে শীর্ষ পারফরমার",
    "National camp scholarship": "জাতীয় ক্যাম্প বৃত্তি",
    "Federation Cup medallist": "ফেডারেশন কাপ পদকজয়ী",
    "Selected for high-performance unit": "উচ্চ-পারফরম্যান্স ইউনিটে নির্বাচিত",

    # ---- Coach license pool (COACH_LICENSES) ----
    "BOA Level I": "বিওএ লেভেল ১",
    "BOA Level II": "বিওএ লেভেল ২",
    "BOA Level III (Elite)": "বিওএ লেভেল ৩ (এলিট)",
    "AFC/Asian Federation Certified": "এএফসি/এশিয়ান ফেডারেশন সনদপ্রাপ্ত",
    "International Instructor": "আন্তর্জাতিক প্রশিক্ষক",
    "AFC/International Pro Licence": "এএফসি/আন্তর্জাতিক প্রো লাইসেন্স",
}


# --------------------------------------------------------------------------- #
#  SECTION TITLE TRANSLATIONS (used by app.py's _stt() helper)                 #
# --------------------------------------------------------------------------- #
SECTION_TITLES_BN: dict[str, str] = {
    "Achievements &amp; highlights": "অর্জন ও কৃতিত্ব",
    "Availability breakdown": "প্রাপ্যতার বিশ্লেষণ",
    "Biometrics &amp; vitals": "শারীরিক পরিমাপ ও গুরুত্বপূর্ণ তথ্য",
    "Calorie intake vs burn": "ক্যালরি গ্রহণ বনাম খরচ",
    "Career progress trend": "ক্যারিয়ার অগ্রগতির প্রবণতা",
    "Career summary": "ক্যারিয়ার সারসংক্ষেপ",
    "Career timeline": "ক্যারিয়ার সময়রেখা",
    "Coach Directory": "কোচ ডিরেক্টরি",
    "Coach feedback": "কোচের মন্তব্য",
    "Compare with another athlete": "অন্য অ্যাথলিটের সাথে তুলনা",
    "Division → Sport composition": "বিভাগ → খেলার গঠন",
    "Elite athletes by sport": "খেলাভিত্তিক এলিট অ্যাথলিট",
    "Export this profile": "এই প্রোফাইল এক্সপোর্ট করুন",
    "Fitness component index by athlete": "অ্যাথলিটভিত্তিক ফিটনেস সূচক",
    "Fitness profile": "ফিটনেস প্রোফাইল",
    "Grassroots reach across Bangladesh": "সারা বাংলাদেশে তৃণমূল সম্প্রসারণ",
    "Injury &amp; availability": "ইনজুরি ও প্রাপ্যতা",
    "Key insights": "মূল পর্যবেক্ষণ",
    "Monthly disbursement trend": "মাসিক বিতরণের প্রবণতা",
    "National &amp; international results": "জাতীয় ও আন্তর্জাতিক ফলাফল",
    "Participation by gender": "লিঙ্গভিত্তিক অংশগ্রহণ",
    "Payment register — this month": "অর্থপ্রদান নিবন্ধন — এই মাস",
    "Personal information": "ব্যক্তিগত তথ্য",
    "Ranking details": "র‍্যাঙ্কিং বিস্তারিত",
    "Registrations by discipline": "বিষয়ভিত্তিক নিবন্ধন",
    "Season-by-season": "মৌসুমভিত্তিক",
    "Sport Rule Books": "খেলার নিয়মাবলী",
    "Sports News Center": "ক্রীড়া সংবাদ কেন্দ্র",
    "Squad readiness": "দলের প্রস্তুতি",
    "Stars by disbursement method": "বিতরণ পদ্ধতি অনুযায়ী তারকা",
    "Stars by division": "বিভাগভিত্তিক তারকা",
    "Talent pathway funnel": "প্রতিভা অনুসন্ধান ধাপসমূহ",
    "Talent pipeline — grassroots to elite": "প্রতিভা পাইপলাইন — তৃণমূল থেকে এলিট",
    "Talent pool by sport &amp; grade": "খেলা ও গ্রেড অনুযায়ী প্রতিভা পুল",
    "This month's status": "এই মাসের অবস্থা",
    "Top performers nationwide": "দেশজুড়ে শীর্ষ পারফরমার",
    "Training attendance": "প্রশিক্ষণ উপস্থিতি",
    "Training load vs availability": "প্রশিক্ষণ লোড বনাম প্রাপ্যতা",
    "VO₂ Max distribution": "VO₂ ম্যাক্স বণ্টন",
    "VO₂ Max vs Body Fat": "VO₂ ম্যাক্স বনাম শরীরের চর্বি",
    "Weighted score contribution": "ওজনযুক্ত স্কোর অবদান",
    "Within-sport ranking model": "খেলাভিত্তিক র‍্যাঙ্কিং মডেল",
}
