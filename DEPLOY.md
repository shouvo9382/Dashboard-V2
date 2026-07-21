# 🚀 Deploy to Streamlit Community Cloud — Step by Step

This puts your dashboard on Streamlit's servers and gives you a **permanent
public URL** (`https://your-name.streamlit.app`). Once it's up:

- ✅ Anyone opens it in a browser — nothing to install
- ✅ Your PC can be **off**. You host nothing.
- ✅ It's protected by an **access code** (the athlete data stays private)
- ✅ Free

You'll do this once. Budget about **20 minutes** the first time.

You need two free accounts: **GitHub** (stores the code) and **Streamlit
Community Cloud** (runs it). Community Cloud signs in *with* your GitHub
account, so really it's one signup.

---

## Part 1 — Put the code on GitHub

Streamlit Cloud runs your app *from a GitHub repository*, so the folder has to
live there first. Easiest path is GitHub Desktop (no command line).

### 1.1 — Create a GitHub account
Go to **https://github.com** and sign up (skip if you have one).

### 1.2 — Install GitHub Desktop
Download from **https://desktop.github.com**, install, and sign in with your
GitHub account.

### 1.3 — Make a new repository
In GitHub Desktop: **File ▸ New Repository**.
- **Name:** `sports-dashboard`
- **Local path:** pick a location (NOT inside your existing `sports_dashboard`
  folder — somewhere fresh, e.g. `C:\Users\Shouv\repos`)
- Leave the rest as-is, click **Create Repository**.

### 1.4 — Copy your project files in
Open the new repo folder (GitHub Desktop ▸ **Repository ▸ Show in Explorer**).
Copy **everything** from your working `sports_dashboard` folder into it —
`app.py`, `scoring.py`, `requirements.txt`, `.gitignore`,
`secrets.toml.example`, the `.streamlit/`, `assets/`, and `data/` folders.

> ✅ **Do** include `data/Dashboard_Data.xlsx` — the app needs it.
> ❌ **Do NOT** include `.venv/` or `.streamlit/secrets.toml`. The `.gitignore`
> already excludes them, so if you copied them by accident, GitHub Desktop
> will correctly ignore them. Confirm neither appears in the changes list.

### 1.5 — Verify the .gitignore is working
Back in GitHub Desktop, look at the list of files on the left. You should see
your code files. You should **NOT** see `.venv` or `secrets.toml`. If you do
see `secrets.toml` (not the `.example` one), **stop** — do not commit. Make
sure `.gitignore` was copied in.

### 1.6 — Commit and publish
- Bottom-left: type a summary like `Initial dashboard` and click
  **Commit to main**.
- Top bar: click **Publish repository**.
- **Tick "Keep this code private."** ← important; the repo shouldn't be public.
- Click **Publish Repository**.

Your code is now on GitHub, privately.

---

## Part 2 — Deploy on Streamlit Community Cloud

### 2.1 — Sign in
Go to **https://share.streamlit.io** and **Continue with GitHub**. Approve the
permissions so Streamlit can see your repositories.

### 2.2 — Create the app
- Click **Create app** (top-right).
- Choose **Deploy a public app from GitHub** / "I have an app".
- **Repository:** `your-username/sports-dashboard`
- **Branch:** `main`
- **Main file path:** `app.py`

### 2.3 — Set the access code (Advanced settings) — DON'T SKIP
Click **Advanced settings**.
- **Python version:** 3.12 is fine.
- **Secrets:** paste exactly this line, with your own code:

  ```toml
  app_password = "YourMinistryCode2026"
  ```

Pick something you're happy to share with viewers but that isn't guessable.
This is what turns the login on.

### 2.4 — Deploy
Click **Deploy**. Watch the log; first build takes a few minutes while it
installs `requirements.txt`. When it finishes, your dashboard loads — showing
the **🔒 Restricted access** screen. Enter your code to confirm it works.

### 2.5 — Get your link
Your URL looks like `https://sports-dashboard-xxxx.streamlit.app`. You can make
it memorable: app **Settings ▸ General ▸ App URL** lets you set a custom
subdomain (e.g. `bd-sports-demo.streamlit.app`).

---

## Part 3 — Share it

Send two things to whoever needs access:

```
Link:  https://your-app.streamlit.app
Code:  YourMinistryCode2026
```

That's the entire handoff. They open the link, type the code once, and use it.
No install, no tunnel, no dependency on you.

---

## Updating the dashboard later

Change `app.py` (or any file) in your **repo** folder, then in GitHub Desktop:
**Commit to main ▸ Push origin**. Streamlit Cloud redeploys automatically
within a minute or two. You never touch the Cloud console again for code
changes.

To change the **access code**: app **Settings ▸ Secrets**, edit the line,
save. No redeploy needed.

---

## Important notes

- **Sleeping:** free apps go to sleep after a period with no visitors. The next
  visitor sees a "waking up" screen for ~30 seconds, then it loads. Before a
  live presentation, **open the link yourself a few minutes early** to wake it.
- **Privacy:** the access code is the only thing between the public internet and
  named athletes' health data. Treat it like a password. Change it after the
  demo if it was shared widely.
- **The repo is private**, but the *deployed app* is reachable by anyone with
  the URL — which is exactly why the access code matters.
- **Data file:** because `data/Dashboard_Data.xlsx` is committed to a private
  repo, only people you grant repo access can see the raw file; app viewers only
  see what the dashboard shows (behind the code).

---

## If something fails

| Problem | Fix |
|---|---|
| Build fails on "installing requirements" | Check `requirements.txt` was committed and is unmodified |
| App loads but says "file not found" | `data/Dashboard_Data.xlsx` wasn't committed — add it, push again |
| No login screen appears | You skipped the Secrets step — add `app_password` in Settings ▸ Secrets |
| "This app is over its resource limits" | Too many viewers at once on free tier; wait, or reboot from the app menu |
| Changes don't show up | You committed but didn't **Push origin** in GitHub Desktop |

Streamlit's own guide: **https://docs.streamlit.io/deploy/streamlit-community-cloud**
