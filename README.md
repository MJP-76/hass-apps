# MJP's Home Assistant Apps

Central repository of Home Assistant **add-ons** (apps) built and maintained by
MJP-76. Each top-level folder is one add-on; Home Assistant's add-on store reads
[`repository.yaml`](repository.yaml) to list them.

## Apps

| App | What it does |
| --- | --- |

## Installing

1. In Home Assistant: **Settings → Add-ons → ⋮ (top right) → Repositories**.
2. Add `https://github.com/MJP-76/hass-apps`.
3. Refresh, open the app you want, **Install**, then **Start**.

## Principles for this repository

- **Wrappers, not forks.** Apps reference upstream projects at a *pinned commit*
  and add only small patches (kept in `patches/` and submitted upstream so they
  eventually disappear).
- **No secrets, ever.** Credentials belong in add-on options (stored by your
  Home Assistant Supervisor), never in this repository.
- **Attribution preserved.** Each app ships its upstream license.

## Adding a new app

Create a top-level folder with at least `config.yaml` (the add-on manifest) and
a `Dockerfile`, add a row to the table above, commit, and the add-on store will
pick it up after a repository refresh.
