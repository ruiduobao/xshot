---
name: xshot
description: Screenshot an X (Twitter) post as it appears in the X web interface (author, text, media, timestamp, engagement counts) and save it as a PNG. Use when an article, post or report cites an X post and needs a faithful screenshot of the source post. Requires a twscrape accounts database for login cookies.
---

# xshot — X post screenshot

## Run it

```bash
./xshot <post-url> -o <output.png>
./xshot <status-id> --user <handle> -o <output.png>
```

(From the repo root; run `./install.sh` once first if `.venv` is missing.)

## Contract

- Success: exit code 0 and one JSON line on stdout:
  `{"ok": true, "path": ..., "width": ..., "height": ..., "url": ...}`
- Exit code 2: the post card never appeared — most often the twscrape
  account cookies expired. Tell the user the X login in the accounts
  database needs refreshing; do not retry in a loop.
- A run takes ~30 seconds. The output is the post card only, in the post's
  original language (auto-translate is switched off for the view).

## Notes

- Login cookies come from a twscrape `accounts.db` (`--db`, `$XSHOT_DB`,
  `./accounts.db`, `~/.twscrape/accounts.db`). Never print cookie values.
- Uses Playwright Firefox on purpose: Chromium cannot traverse
  TLS-intercepting proxies (ERR_TUNNEL_CONNECTION_FAILED). Do not "fix"
  this by switching engines.
