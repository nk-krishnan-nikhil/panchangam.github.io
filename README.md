# Malayalam Panchangam Public Calendar

This project generates a **Malayalam Panchangam** calendar feed (`.ics`) that can be:

- hosted as a public URL
- subscribed to from Google Calendar
- auto-updated daily via GitHub Actions

## What This Includes

- Daily Panchangam details per date
- Malayalam solar date (Kollavarsham + month + day)
- Tithi, Nakshatra, Yoga, Karana
- Sunrise, Sunset
- Rahukalam, Gulikakalam, Yamagandam
- Era year references (Saka, Vikrama, Kali)

## 1. Generate the Calendar File

Run from the project root:

```bash
python scripts/generate_malayalam_calendar.py --start 2026-01-01 --end 2027-12-31 --output public/malayalam-panchangam.ics
```

Location defaults to Thiruvananthapuram. Use custom location if needed:

```bash
python scripts/generate_malayalam_calendar.py \
  --start 2026-01-01 \
  --days 730 \
  --latitude 9.9312 \
  --longitude 76.2673 \
  --location-name "Kochi" \
  --output public/malayalam-panchangam.ics
```

## 2. Publish as a Public Link (GitHub Pages)

1. Push this repository to GitHub.
2. Open repository settings -> **Pages**.
3. Set source to **Deploy from a branch**.
4. Select branch `main` and folder `/public`.
5. Save.

Your public calendar link will be:

```text
https://<github-username>.github.io/<repo-name>/malayalam-panchangam.ics
```

## 3. Add to Google Calendar (Subscription)

1. Open Google Calendar.
2. Click **Other calendars** -> **From URL**.
3. Paste the `.ics` URL above.
4. Click **Add calendar**.

Google will periodically refresh subscribed URLs (not instant).

## 4. Auto-Update Daily

This repo includes `.github/workflows/update-calendar.yml`.

It regenerates `public/malayalam-panchangam.ics` every day and commits changes.

To use it:

1. Enable GitHub Actions for your repo.
2. Ensure workflow permissions allow write access to contents:
   - Settings -> Actions -> General -> Workflow permissions -> **Read and write permissions**.

## Notes

- Calculations are location-sensitive; keep latitude/longitude aligned with your target city.
- This is a computational Panchangam feed using Surya Siddhanta style formulas and can vary slightly from specific printed almanacs.
