# 5110-frc-scouting-test

Browser apps for match scouting. They work without internet and pass data by QR code.

**Live site:** https://YOUR-GITHUB-USERNAME.github.io/5110-frc-scouting-test/

| Page | Link | Used on |
|---|---|---|
| Home | [index.html](https://YOUR-GITHUB-USERNAME.github.io/5110-frc-scouting-test/) | Pick team, season and event, then open either app with that event |
| Scout | [scout.html](https://YOUR-GITHUB-USERNAME.github.io/5110-frc-scouting-test/scout.html) | Scouts' tablets and phones. Record a match and show a QR code. |
| Analysis | [analysis.html](https://YOUR-GITHUB-USERNAME.github.io/5110-frc-scouting-test/analysis.html) | Scanning laptop. Scan QR codes, view records, team stats and the schedule, export CSV/JSON. |

*Replace `YOUR-GITHUB-USERNAME` with your GitHub user or organization name. If you rename the
repository, also change `5110-frc-scouting-test` in these links.*

| File | Purpose |
|---|---|
| `config.js` | **The fields being scouted** and the TBA values to pull. Edit this for each season's game. |
| `tba-events.txt` | Teams (and seasons) and extra events to download from The Blue Alliance. |
| `tba.js` | Loads the TBA data the website publishes. Both apps use it. |
| `sheet.js` | Sends saved matches to the team's Google Sheet and reads them back. Both apps use it. |
| `scripts/google-sheet.gs` | The script to paste into the Google Sheet (see *Google Sheet backup*). |
| `scripts/fetch_tba.py` | Downloads TBA data using the secret key, and Statbotics data (no key needed). Run by GitHub Actions. |
| `.github/workflows/pages.yml` | Publishes the site with fresh TBA data every 15 minutes. |
| `lib/` | Bundled QR libraries (qrcode-generator, jsQR), so nothing is loaded from the internet. |

## Publishing on GitHub (once)
1. Push this folder to a GitHub repository named `5110-frc-scouting-test`, on the `main` branch.
2. Go to **Settings → Pages**. Under *Build and deployment*, set **Source** to **GitHub Actions**.
3. Go to **Settings → Secrets and variables → Actions** and click **New repository secret**. Name it
   `TBA_KEY` and paste your read key from https://www.thebluealliance.com/account.
4. Go to **Actions → Deploy site with TBA data** and click **Run workflow**. The site is live a
   minute or two later.

### How the TBA key stays secret
The key is used only in GitHub Actions, never in a web page. Anything a web page uses can be read
by anyone who opens it, so the key must never go in `config.js` or any other file in this repository.
Every 15 minutes, the workflow uses the key to download what `tba-events.txt` lists. It then
publishes the data as plain JSON files in `tba/`. TBA data is public, so publishing it is fine.
The apps load those files from the website, and no device ever needs the key.

- **To choose what is downloaded:** edit `tba-events.txt` on GitHub. The commit republishes the site.
  A line like `team 5110 2025 2026` downloads every event team 5110 is registered for in those
  seasons, so new registrations show up by themselves. A line with an event code, such as
  `2026miket`, adds one more event your team isn't registered for (to scout ahead, for example).
- **To update right away:** click **Actions → Deploy site with TBA data → Run workflow**. Otherwise
  wait for the next 15-minute run. GitHub sometimes runs scheduled jobs late when it is busy.
- **Between seasons:** turn the schedule off at **Actions → Deploy site with TBA data → ⋯ → Disable
  workflow**. Turn it back on before the next event.
- **If the key leaks:** delete it at thebluealliance.com/account, make a new one and update the
  `TBA_KEY` secret.

## Google Sheet backup (optional)
Every saved match can also go to a shared Google Sheet. Scout sends each match when it's saved, or
later if there's no internet. Analysis has an **Update from Sheet** button, and also updates by itself
every 2 minutes, so it picks up every tablet's matches without scanning. QR codes still work as the
offline backup.

**Setup (once):**
1. Create a Google Sheet. Open **Extensions → Apps Script**, delete what's there, paste in all of
   `scripts/google-sheet.gs` and save.
2. Click **Deploy → New deployment**, choose type **Web app**, and set *Execute as* **Me** and
   *Who has access* **Anyone**. Click **Deploy** and allow access when Google asks.
3. Copy the **Web app URL** (it ends in `/exec`). On the analysis laptop, paste it under
   **Google Sheet → Web-app URL** and press **Save URL**.
4. Press **Copy tablet setup link** and send the link privately to scouts (team chat, not a public
   page). Opening it on a tablet stores the URL there. You can also paste the URL under
   **Setup → Google Sheet backup** in Scout.

The Sheet gets one row per event, match and station. A newer save replaces the row. The `json`
column is what the apps read back, so don't edit it. You can rename the other headers.

**Keeping the URL private:** the URL is never in this repository or on the website. It is only on
devices where someone entered it or opened the setup link. Anyone who has it can add rows, so share
it only with the team. If it leaks, in Apps Script go to **Deploy → Manage deployments**, archive the
old deployment and create a new one, then send out a new setup link. The old URL stops working.

**After changing `google-sheet.gs`:** go to **Deploy → Manage deployments → Edit**, and choose
**New version**. This keeps the same URL.

## Picking the event (home page)
On the home page, enter your team number, then pick the season and one of the events the team is
registered for. The list also includes any extra events in `tba-events.txt`. The **Scout** and
**Analysis** links then open with that event already filled in, and each app loads the event's TBA
data straight away. The home page remembers your choice. The apps' header links also pass the
event along, so switching from Scout to Analysis keeps it.

## Getting the scout app onto tablets
On each tablet, while online, pick the event on the home page, open **Scout** and choose
*Add to Home Screen*. After that, it keeps working with no connection. Scouts can still change the
event code by hand in *Setup*.

## Running the analysis laptop
Open the Analysis link. Cameras work on the GitHub site because it uses `https://`. You can also
use a USB or Bluetooth handheld 2D barcode scanner. Click the "Handheld scanner" box and scan.
Once opened, the page also works offline.

For testing without GitHub, cameras also work on `http://localhost`:
```
cd 5110-frc-scouting-test
python3 -m http.server 8000          # then open http://localhost:8000/
TBA_KEY=yourkey python3 scripts/fetch_tba.py  # optional: TBA data for local testing (not committed)
```

## Workflow at an event
1. Each scout enters their name, the event code and their driver station once. These are remembered.
2. For each match, check the team number and tap through the match.
3. Press **Show QR code** and hold it up to the analysis laptop. It beeps when the record is added.
   Press **Back**, then **Save match**. This saves the match on the device and moves on to the next one.
4. If the analysis laptop missed a match, find it under **Saved on this device** and press **Show QR**.
   To send everything at once, press **Show all as QR**. If the matches don't fit in one code, the app
   splits them into several. Scan each one, using **Next code →**. You can scan them in any order, and
   scanning a match twice is harmless.
5. If Scout and Analysis are used on the **same device**, nothing needs scanning. Analysis picks up
   matches saved on that device when it opens, and right away when Scout saves in another tab.
   A match deleted in Analysis stays deleted until Scout saves that match again.
5. Export a CSV from the analysis laptop for Excel, Google Sheets or Tableau.

Scanning the same match and station twice replaces the earlier record, so re-scans are harmless.
Data is stored in each browser's local storage. Export a JSON backup now and then, and use
**Load JSON…** to merge data from another analysis laptop.

## The Blue Alliance data
Internet is needed only while loading TBA data. It is then saved on each device and keeps working
offline. The event must be one of your team's events, or be listed in `tba-events.txt`.

**Scout tablets:** opening Scout from the home page loads the schedule. To reload it, open **Match
schedule from The Blue Alliance** under *Setup* and press **Download schedule**. After that, the team
number fills in from the match number and driver station, with the team name under it. If a scout
types a different team, the app warns them but still lets them save.

**Analysis:** opening Analysis from the home page loads the event's data. Press **Update TBA
data** again when you are online to get new scores, OPRs and rankings. This adds:
- *Match records*: a team name column and a **Schedule check**. The check flags records where the
  scouted team isn't the team TBA has in that match and station.
- *Team averages*: every team at the event (including teams nobody has scouted yet), with rank,
  W-L-T, ranking score, OPR, DPR and CCWM. **Export team CSV** saves this table for pick lists.
- *Schedule*: every qualification match, with ✓ for robots scouted. Played matches that are
  missing a robot are shown in red.

**Official game data (2026 REBUILT).** After matches are played, TBA also has each match's
score breakdown, and the analysis app adds it:
- *Match records*: TBA's official auto and endgame tower level (0-3) for the robot. Use this to
  check what the scout recorded.
- *Team averages*: average tower levels and how often the robot climbed. It also shows how often
  the team's alliance earned the Energized, Supercharged and Traversal RPs, and cOPRs for auto,
  teleop and total fuel and for tower points. FMS counts fuel per alliance, not per robot, so cOPR
  estimates each team's share by least squares across all its matches. Expect cOPR to be noisy
  until each team has played 5 or 6 matches.

Which values are pulled is set in the `tba` section of `config.js`. Update it each season, like
the scouting fields. Only qualification matches are used.

**Statbotics.** The same workflow also downloads [Statbotics](https://www.statbotics.io) data for
each event. It needs no key. If Statbotics is down, the TBA data is still published without it.
EPA (Expected Points Added) estimates how many points a robot adds to its alliance. Unlike OPR, it
carries over from the team's earlier events, so it is already useful before the first match.
- *Team averages*: EPA, auto/teleop/endgame EPA, EPA at the start of the event and the season
  best, world EPA rank and percentile, and the season W-L-T and win rate across all events.
- *Schedule*: predicted scores, red's chance to win and each alliance's chance at each RP. They
  are greyed out once a match is played. Your team (picked on the home page) is shown in blue.
- The status line under **Update TBA data** shows the event's average, top 8 and best EPA, and
  how often Statbotics has picked the winner so far.

The `statbotics` section of `config.js` sets extra EPA columns for this season's game and the RP
names. Statbotics' names for the values change each season. The **Deploy site with TBA data** log
lists them for each event ("Statbotics EPA breakdown names for …"), so you can copy the ones you want.

## Changing the fields
Edit `config.js`. You can use these field types: `counter`, `checkbox`, `select`, `rating`
and `text`. Keep the keys short, because they go inside every QR code. If you change fields
during an event, increase `version`. The analysis app will warn when it scans data from a
different version. Have every tablet reload the Scout page while online.
