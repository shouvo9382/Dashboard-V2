# 🏅 Athlete Dashboard — Presenter Guide

**You do not need to know any programming to run this.**
Everything happens by double-clicking one file.

---

## Before the presentation day (do this once, with internet)

> ⚠️ **Do this at home or in the office — NOT five minutes before you present.**
> The first run downloads some software and takes about 2 minutes.

### Step 1 — Check you have Python

Open the Start menu, type `cmd`, press Enter, then type:

```
python --version
```

- If you see something like `Python 3.12.4` → you're ready. Go to Step 2.
- If you see an error, or a number **below 3.10** → install Python from
  **https://python.org**. During setup, **tick the box that says
  "Add Python to PATH"**. This box is easy to miss and nothing works without it.

### Step 2 — Unzip the folder

Unzip `bangladesh_sports_dashboard.zip` somewhere you'll find it again —
your **Desktop** is a good choice. You should end up with a folder called
`sports_dashboard`.

Do not rename anything inside it.

### Step 3 — Double-click `run_dashboard.bat`

Inside the folder, double-click **`run_dashboard.bat`**.

A black window opens and shows setup messages. Wait ~2 minutes.
Your browser will open the dashboard automatically.

> **If Windows shows a blue "Windows protected your PC" warning:**
> click **More info** → **Run anyway**. This appears because the file
> isn't digitally signed, not because anything is wrong with it.

### Step 4 — Confirm it works, then close it

Click through the sidebar pages. When happy, **close the black window.**
That shuts the dashboard down.

**You are now set up.** Every future run takes about 10 seconds and
**needs no internet at all.**

---

## On presentation day

1. Double-click **`run_dashboard.bat`**
2. Wait ~10 seconds. The browser opens.
3. Press **F11** for fullscreen. Present.
4. When finished, **close the black window.**

That's the whole procedure.

### Rules while presenting

- ✅ **Keep the black window open.** Minimise it, don't close it.
- ✅ You do **not** need internet or Wi-Fi.
- ❌ Closing the black window kills the dashboard mid-demo.

---

## Driving the dashboard

**Sidebar, top:** the five pages — Executive Summary, Player Profile,
Performance & Fitness, Injury & Training, Rankings & Leaderboard.

**Sidebar, middle:** pick a **Sport**, then a **Player**. The Player list
automatically shows only athletes from the sport you chose.

**Sidebar, bottom:** ⚙️ **Ranking model weights**.

### The best 30 seconds of the demo

1. Go to **Rankings & Leaderboard**, set Sport to **Cricket**.
2. Open **⚙️ Ranking model weights**.
3. Drag **Performance** to the far right, and **Fitness** to the far left (zero).
4. Watch the leaderboard reorder itself instantly.
5. Click **↺ Reset to defaults**.

This shows the ministry that the ranking model is *theirs to tune*, not a
black box. It is the single most persuasive moment in the dashboard.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| "Python is not installed" | Install from python.org, **tick "Add Python to PATH"**, restart the laptop |
| "Windows protected your PC" | **More info** → **Run anyway** |
| Black window flashes and vanishes | Run `run_dashboard_alt_port.bat` instead |
| Browser doesn't open | Type `http://localhost:8501` into Chrome manually |
| "Port 8501 is already in use" | Close the other black window, or run `run_dashboard_alt_port.bat` |
| "Package install failed" | You're offline. Connect to internet, delete the `.venv` folder, try again |
| Dashboard freezes | Close the black window, double-click `run_dashboard.bat` again |

**Nuclear option:** delete the `.venv` folder inside `sports_dashboard`,
then double-click `run_dashboard.bat` again. This rebuilds everything from
scratch (needs internet, ~2 min).

---

## Mac users

Same steps, but double-click **`run_dashboard.command`** instead.

The first time, macOS may block it. Right-click the file → **Open** →
**Open** again in the dialog. If it still refuses, open Terminal, type
`chmod +x ` (with a trailing space), drag the file in, and press Enter.

---

## A note on the data

This dashboard shows **real, named athletes** with injury histories and
body-composition figures. Because it runs entirely on this laptop, none of
that data is uploaded anywhere or sent over the internet.

Please don't post screenshots of individual player profiles publicly.
