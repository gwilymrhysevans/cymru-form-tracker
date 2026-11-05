# Cymru Form Tracker — public launch

This folder is the **website only**. It contains no PitchAPI key, identity registry, or raw API cache.

## Publish the first version

1. Create a GitHub repository, e.g. `cymru-form-tracker` (public is simplest for public Streamlit hosting).
2. Use **Add file → Upload files** in that repository. Upload the **contents of this folder** (the `app.py`, `requirements.txt`, and the `data` directory). `DEPLOY-README.md` may be included but isn't necessary. Preserve the `data` directory.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Click **Create app**, select your repository and `main` branch, and set the entrypoint to `app.py`.
5. Choose an available subdomain, e.g. `cymru-form-tracker`, and deploy.
6. Test the leaderboard, select a row to open a profile, test Compare, and check the updated-at timestamp.

No PitchAPI key is needed on Streamlit Community Cloud. The live site reads the four derived CSVs in `data/`.

## Keeping the published site current

In your **private working folder** on your Windows PC, run:

1. `REFRESH.cmd` — collects new match data and updates local output.
2. `EXPORT PUBLIC.cmd` — creates a fresh `public_site` directory.
3. Update the GitHub repository's `data/*.csv`, `data/updated_at.txt` and `app.py` (if the dashboard changed). Commit the changes. The hosted site reloads from GitHub.

**Do not upload the private working folder**, which includes `cache/`, `player_registry.csv`, the PitchAPI key's local context, and review logs.

## Twice-weekly refresh — after launch

Recommended Monday and Thursday, after league matches. This is optional, and **Windows Task Scheduler alone does not publish refreshed files to GitHub**. For full automation you'll also need a GitHub push step (or a GitHub Actions job with a securely stored API key), and you should confirm API rate limits, licensing/redistribution permissions and data quality before enabling unattended uploads.

For a simple start, refresh and publish manually twice a week. The public data remains the last published snapshot between updates.

## Before sharing publicly

Check that PitchAPI's agreement permits public display or redistribution of the derived match ratings and stats. The export intentionally excludes raw cached responses and internal player IDs, but its tables still contain provider-derived data.
