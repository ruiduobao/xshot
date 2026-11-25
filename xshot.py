# -*- coding: utf-8 -*-
"""
xshot — screenshot an X (Twitter) post as it appears in the X web interface.

Captures the post card itself (author, text, media, timestamp, engagement
counts) as a PNG — handy when an article or report about a post needs a
faithful screenshot of the source post.

Login state is reused from a twscrape accounts database (read-only): the
active account's cookies (auth_token + ct0) are injected into the browser.
Cookie values are never printed or written anywhere.

Why Firefox: some networks sit behind TLS-intercepting proxies whose CA is
trusted by the OS but not by Chromium's bundled trust store, which makes
Chromium fail with ERR_TUNNEL_CONNECTION_FAILED while Firefox (with
ignore_https_errors) works. Firefox is therefore the default engine.

Usage:
  python xshot.py https://x.com/<user>/status/<id> -o out.png
  python xshot.py <status_id> --user <handle> -o out.png

Options:
  --db PATH        twscrape accounts.db path
                   (default: $XSHOT_DB, else ./accounts.db, else ~/.twscrape/accounts.db)
  --width N        viewport width in CSS px (default 880)
  --scale N        device pixel ratio (default 2)
  --proxy URL      proxy server, e.g. http://user:pass@host:port
                   (default: $https_proxy / $http_proxy from the environment)

Exit codes: 0 success; 2 page did not load / post card not found
(cookies expired?); 3 bad arguments.
On success, one JSON line is printed to stdout:
  {"ok": true, "path": ..., "width": ..., "height": ..., "url": ...}
"""
import argparse, json, os, re, socket, sqlite3, sys
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
      "Gecko/20100101 Firefox/133.0")


def find_db(cli_db: str) -> str:
    candidates = [cli_db, os.environ.get("XSHOT_DB", ""),
                  os.path.join(os.getcwd(), "accounts.db"),
                  os.path.expanduser("~/.twscrape/accounts.db")]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise SystemExit("accounts.db not found; pass --db or set XSHOT_DB "
                     "(a twscrape accounts database is required)")


def load_cookies(db_path: str):
    con = sqlite3.connect(db_path)
    row = con.execute("SELECT cookies FROM accounts WHERE active=1 LIMIT 1").fetchone()
    con.close()
    if not row:
        raise SystemExit("no active account in accounts.db")
    raw = json.loads(row[0])
    return [{"name": k, "value": str(v), "domain": ".x.com", "path": "/"}
            for k, v in raw.items()]


def build_proxy(cli_proxy: str):
    purl = cli_proxy or os.environ.get("https_proxy") or os.environ.get("http_proxy") or ""
    if not purl:
        return None
    u = urlparse(purl)
    host = u.hostname
    try:
        host = socket.gethostbyname(host)
    except Exception:
        pass
    proxy = {"server": f"{u.scheme}://{host}:{u.port}"}
    if u.username:
        proxy["username"] = u.username
    if u.password:
        proxy["password"] = u.password
    return proxy


def normalize_url(arg: str, user: str) -> str:
    if arg.startswith("http"):
        return arg
    if re.fullmatch(r"\d+", arg):
        if not user:
            raise SystemExit("when passing a bare status id, --user <handle> is required")
        return f"https://x.com/{user}/status/{arg}"
    raise SystemExit(f"unrecognized post identifier: {arg}")


def main():
    ap = argparse.ArgumentParser(description="Screenshot an X post card")
    ap.add_argument("target", help="post URL or status id")
    ap.add_argument("-o", "--output", default="", help="output PNG path")
    ap.add_argument("--user", default="", help="author handle (with a bare status id)")
    ap.add_argument("--db", default="", help="twscrape accounts.db path")
    ap.add_argument("--width", type=int, default=880)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--proxy", default="", help="proxy URL (default: env https_proxy)")
    args = ap.parse_args()

    url = normalize_url(args.target, args.user)
    m = re.search(r"status/(\d+)", url)
    out = args.output or f"xshot_{m.group(1) if m else 'post'}.png"

    from playwright.sync_api import sync_playwright

    cookies = load_cookies(find_db(args.db))
    proxy = build_proxy(args.proxy)
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True, proxy=proxy)
        ctx = browser.new_context(viewport={"width": args.width, "height": 1400},
                                  device_scale_factor=args.scale, user_agent=UA,
                                  locale="en-US", ignore_https_errors=True)
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
        except Exception as e:
            print(json.dumps({"ok": False, "error": f"page failed to load: {e}"}))
            return 2
        try:
            page.wait_for_selector('article[data-testid="tweet"]', timeout=45000)
        except Exception:
            print(json.dumps({"ok": False,
                              "error": "post card not found (cookies expired, or post unavailable)"}))
            return 2
        article = page.query_selector('article[data-testid="tweet"]')
        # If the account auto-translates posts, switch back to the original
        # text for this view only (account settings are not changed).
        try:
            for label in ("显示原文", "Show original"):
                b = article.query_selector(f'button:has-text("{label}")')
                if b:
                    b.click()
                    page.wait_for_timeout(900)
                    article = page.query_selector('article[data-testid="tweet"]')
                    break
        except Exception:
            pass
        # Expand truncated long posts.
        try:
            btn = article.query_selector('button[data-testid="tweet-text-show-more-link"], '
                                         'a[data-testid="tweet-text-show-more-link"]')
            if btn:
                btn.click()
                page.wait_for_timeout(800)
                article = page.query_selector('article[data-testid="tweet"]')
        except Exception:
            pass
        # Wait until images are actually loaded.
        try:
            page.wait_for_function(
                "el => Array.from(el.querySelectorAll('img')).every(i => i.complete && i.naturalWidth > 0)",
                arg=article, timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(600)
        article.screenshot(path=out)
        box = article.bounding_box()
        browser.close()
    print(json.dumps({"ok": True, "path": os.path.abspath(out),
                      "width": round(box["width"] * args.scale) if box else None,
                      "height": round(box["height"] * args.scale) if box else None,
                      "url": url}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
