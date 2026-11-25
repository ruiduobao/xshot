# xshot — X (Twitter) post screenshot tool

Screenshot a single X post **as it appears in the X web interface** — author,
full text, media, timestamp and engagement counts — saved as one PNG of the
post card. Built for agents and writers who cite X posts in articles and
need a faithful screenshot of the source post.

## Quick start (for agents)

```bash
git clone https://github.com/ruiduobao/xshot.git
cd xshot
./install.sh            # creates .venv, installs Playwright + Firefox
./xshot https://x.com/<user>/status/<id> -o shot.png
```

On success the tool prints exactly one JSON line to stdout:

```json
{"ok": true, "path": "/abs/path/shot.png", "width": 1196, "height": 1748, "url": "https://x.com/..."}
```

Exit codes: `0` success · `2` page/post did not load (usually expired
cookies) · `3` bad arguments. A run takes ~30 s (page load through a proxy).

## Login requirement

X shows almost nothing to logged-out visitors, so xshot reuses the login
cookies of a [twscrape](https://github.com/vladkens/twscrape) accounts
database (read-only; the active account's `auth_token` + `ct0`). Cookie
values are never printed or stored elsewhere.

Database lookup order: `--db PATH` → `$XSHOT_DB` → `./accounts.db` →
`~/.twscrape/accounts.db`.

## Usage

```bash
./xshot <post-url> [-o out.png] [--width 880] [--scale 2] [--db accounts.db]
./xshot <status-id> --user <handle> -o out.png
```

- The screenshot is the post card element only (no sidebar, no browser chrome).
- If the account has auto-translate on, xshot clicks "Show original" first,
  so the screenshot shows the post in its original language (view-only;
  account settings are untouched). Truncated long posts are expanded.
- Proxy: taken from `$https_proxy`/`$http_proxy`, override with `--proxy`.

## Why Firefox (not Chromium)

Some networks sit behind TLS-intercepting proxies whose CA is trusted by
the OS but not by Chromium's bundled trust store; Chromium then fails every
page with `ERR_TUNNEL_CONNECTION_FAILED`. Firefox driven by Playwright,
with `ignore_https_errors=True`, works in those environments — so xshot
uses Firefox.

## Files

- `xshot.py` — the tool (single file, Python ≥ 3.10, only dependency: Playwright)
- `xshot` — shell wrapper using the local `.venv`
- `install.sh` — one-time setup
- `SKILL.md` — agent skill description of this tool

## License

MIT
