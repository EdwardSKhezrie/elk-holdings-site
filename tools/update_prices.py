#!/usr/bin/env python3
"""Daily price update for the ELK site. Runs on GitHub Actions (.github/workflows/daily-prices.yml).

Updates prices.json (latest close, previous close, date) and history.json (one close per
trading day) from Yahoo Finance daily bars. Only real closes are written: a ticker whose
data can't be fetched is left as it was, and existing history values are never changed.
"""
import json, os, sys, time, urllib.request, urllib.parse
from collections import Counter
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "2026-10-21"          # first date of history.json
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


SRC = Counter()
FAILS = Counter()


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _yahoo(sym):
    q = urllib.parse.quote(sym)
    for host in ("query1", "query2"):
        try:
            res = json.loads(_get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{q}?range=3mo&interval=1d"))["chart"]["result"][0]
            off = res["meta"].get("gmtoffset", -18000)
            out = {}
            for t, c in zip(res.get("timestamp") or [], res["indicators"]["quote"][0].get("close") or []):
                if c is not None:
                    out[datetime.fromtimestamp(t + off, timezone.utc).strftime("%Y-%m-%d")] = c
            if out:
                return out
        except Exception:
            time.sleep(1)
    return None


def _nasdaq(sym):
    frm = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    for ac in ("stocks", "etf"):
        try:
            d = json.loads(_get(f"https://api.nasdaq.com/api/quote/{sym}/historical?assetclass={ac}&fromdate={frm}&limit=90"))
            rows = (((d or {}).get("data") or {}).get("tradesTable") or {}).get("rows") or []
            out = {}
            for r in rows:
                m, dd, y = r["date"].split("/")
                out[f"{y}-{m}-{dd}"] = float(r["close"].replace("$", "").replace(",", ""))
            if out:
                return out
        except Exception:
            pass
    return None


def _stooq(sym):
    try:
        txt = _get(f"https://stooq.com/q/d/l/?s={sym.lower()}.us&i=d")
        out = {}
        for line in txt.strip().splitlines()[1:]:
            p = line.split(",")
            if len(p) >= 5 and p[0] >= START:
                out[p[0]] = float(p[4])
        return out or None
    except Exception:
        return None


def fetch(sym, option=False):
    srcs = [("yahoo", _yahoo)] if option else [("yahoo", _yahoo), ("nasdaq", _nasdaq), ("stooq", _stooq)]
    for name, fn in srcs:
        if FAILS[name] >= 6 and not SRC[name]:      # source looks blocked today: stop wasting time on it
            continue
        out = fn(sym)
        if not out:
            FAILS[name] += 1
            continue
        if out:
            SRC[name] += 1
            return {d: (round(c, 2) if c >= 1 else round(c, 4)) for d, c in out.items()}
    print(f"  ! {sym}: no source returned data", file=sys.stderr)
    return None


def main():
    pp = os.path.join(ROOT, "prices.json")
    hp = os.path.join(ROOT, "history.json")
    P = json.load(open(pp))
    H = json.load(open(hp))

    # Today's bar is only final after the 4pm ET close (plus a little slack).
    et = datetime.now(timezone.utc) - timedelta(hours=5)
    today = et.strftime("%Y-%m-%d")
    closed = et.hour * 60 + et.minute >= 16 * 60 + 40 or et.weekday() >= 5

    series, missing, odd = {}, [], []
    for tk in sorted(P["t"]):
        s = fetch(tk)
        time.sleep(0.2)
        if not s:
            missing.append(tk)
            continue
        if not closed:
            s.pop(today, None)
        series[tk] = s

    updated = 0
    for tk, s in series.items():
        rec = P["t"][tk]
        days = sorted(s)
        newest = days[-1]
        if rec.get("lastDate") and newest <= rec["lastDate"]:
            continue
        last, ref = s[newest], rec.get("last")
        if ref and not (0.4 < last / ref < 2.5):      # split or bad print: don't trust it blindly
            odd.append(f"{tk} {ref}->{last}")
            continue
        prev = s[days[-2]] if len(days) > 1 else ref
        rec["prev"], rec["last"], rec["lastDate"] = prev, last, newest
        if rec.get("buy") is None:
            rec["buy"], rec["buyDate"] = last, newest
        updated += 1

    # Option contracts (e.g. SNXX270115C00009000): last traded price per share
    for sym, q in (P.get("opt") or {}).items():
        s = fetch(sym, option=True)
        if s:
            if not closed:
                s.pop(today, None)
            if s:
                d = max(s)
                if not q.get("date") or d >= q["date"]:
                    q["last"], q["date"] = s[d], d

    dates_all = [r["lastDate"] for r in P["t"].values() if r.get("lastDate")]
    P["asof"] = Counter(dates_all).most_common(1)[0][0]

    # history.json: add every real trading date between START and asof; never overwrite a value
    old = H["dates"]
    newd = set(old)
    for s in series.values():
        newd.update(d for d in s if START <= d <= P["asof"])
    dates = sorted(newd)
    T = {}
    for tk in sorted(set(H["t"]) | set(P["t"])):
        prior = dict(zip(old, H["t"].get(tk, [])))
        s = series.get(tk, {})
        T[tk] = [prior[d] if prior.get(d) is not None else s.get(d) for d in dates]
    # keep only dates where at least a handful of tickers traded (drops stray holiday bars)
    keep = [i for i, d in enumerate(dates) if d in old or sum(T[t][i] is not None for t in T) >= 10]
    H = {"dates": [dates[i] for i in keep], "t": {t: [v[i] for i in keep] for t, v in T.items()}}

    with open(pp, "w") as f:
        json.dump(P, f, indent=0)
        f.write("\n")
    with open(hp, "w") as f:
        json.dump(H, f, separators=(",", ":"))

    summary = (f"Run {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC: updated {updated} of {len(P['t'])} tickers to {P['asof']}; "
               f"sources {dict(SRC)}; no data: {', '.join(missing) or 'none'}; skipped: {', '.join(odd) or 'none'}")
    with open(os.path.join(ROOT, "tools", "last_price_run.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"Updated {updated} tickers; prices as of {P['asof']}; history has {len(H['dates'])} days "
          f"({H['dates'][0]} to {H['dates'][-1]}).")
    if missing:
        print("No data:", ", ".join(missing))
    if odd:
        print("Skipped (price jump >2.5x, check for a split):", ", ".join(odd))
    opt = P.get("opt") or {}
    for k, q in opt.items():
        print(f"Option {k}: {q}")


if __name__ == "__main__":
    main()
