#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Halal Market Ledger — daily report generator.

Fetches the 112-security universe, scores the 100 stocks, writes today's report
page, appends the run to data/history.json and rebuilds index.html.

    python3 generate_report.py            # normal run
    python3 generate_report.py --dry-run  # fetch + score, write nothing
    python3 generate_report.py --date 2026-08-25   # override the run date

Exit codes:  0 success · 1 too many fetch failures (nothing written) · 2 setup error
"""
import argparse, datetime, json, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from universe import US_STOCKS, CA_STOCKS, FUNDS
from fetch_data import fetch_stock, fetch_fund, reconcile, FetchError
from scoring import evaluate
import investor_tweets
import thirteen_f
import render_report
import build_site

# A run is abandoned rather than published if fewer than this share succeeds.
MIN_STOCK_COVERAGE = 0.80

REPORT_HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Halal Market Ledger — %(label)s</title>
<meta name="description" content="Shariah-screened review of 112 securities for %(label)s.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%%22http://www.w3.org/2000/svg%%22 viewBox=%%220 0 100 100%%22><text y=%%22.9em%%22 font-size=%%2290%%22>&#127769;</text></svg>">
<style>*{margin:0;padding:0}</style>
</head>
<body>
<script>(function(){try{var t=localStorage.getItem('hml-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>
'''

REPORT_TAIL = '''
<div style="max-width:1180px;margin:0 auto;padding:0 22px 60px">
<a href="../index.html" style="display:inline-block;color:var(--jade);text-decoration:none;font-size:13.5px;font-family:'DM Sans',sans-serif">&larr; All reports</a>
</div>
%s
</body></html>'''

STARS_JS = '''<script>
(function(){
  var c=document.getElementById('stars'); if(!c) return;
  var x=c.getContext('2d'), dpr=Math.min(window.devicePixelRatio||1,2);
  function col(){return getComputedStyle(document.documentElement).getPropertyValue('--star').trim()||'#1a6b57';}
  function star8(cx,cy,R){var r=R*0.414,p=[];
    for(var i=0;i<16;i++){var a=(Math.PI/8)*i-Math.PI/2,rad=(i%2===0)?R:r;p.push([cx+Math.cos(a)*rad,cy+Math.sin(a)*rad]);}
    x.beginPath();x.moveTo(p[0][0],p[0][1]);for(var j=1;j<16;j++)x.lineTo(p[j][0],p[j][1]);x.closePath();x.stroke();}
  function draw(){var w=c.clientWidth,h=c.clientHeight;if(!w||!h)return;
    c.width=w*dpr;c.height=h*dpr;x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,w,h);
    x.strokeStyle=col();x.lineWidth=1;x.lineJoin='round';var S=64,R=S*0.52;
    for(var row=-1,yy=-S;yy<h+S;row++,yy+=S){var off=(row%2===0)?0:S/2;
      for(var xx=-S+off;xx<w+S;xx+=S){star8(xx,yy,R);x.beginPath();var q=S*0.5*0.30;
        x.moveTo(xx+S/2,yy+S/2-q);x.lineTo(xx+S/2+q,yy+S/2);x.lineTo(xx+S/2,yy+S/2+q);
        x.lineTo(xx+S/2-q,yy+S/2);x.closePath();x.stroke();}}}
  draw();var t;addEventListener('resize',function(){clearTimeout(t);t=setTimeout(draw,120);});
  if(window.matchMedia){var mq=matchMedia('(prefers-color-scheme: dark)');
    (mq.addEventListener?mq.addEventListener.bind(mq,'change'):mq.addListener.bind(mq))(draw);}
  new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(draw);
})();
</script>'''


def log(msg):
    print("[hml] %s" % msg, flush=True)


def gather(symbols, fetcher, label, failures):
    rows = []
    for i, arg in enumerate(symbols, 1):
        sym = arg[0] if isinstance(arg, tuple) else arg
        try:
            row = fetcher(*arg) if isinstance(arg, tuple) else fetcher(arg)
            for w in reconcile(row):
                row["notes"] = (row["notes"] + " " + w).strip()
                log("  warn %s: %s" % (sym, w))
            rows.append(row)
            log("  %2d/%d %-10s %s" % (i, len(symbols), sym, row.get("price")))
        except (FetchError, Exception) as ex:  # noqa: BLE001
            failures.append(sym)
            log("  %2d/%d %-10s FAILED: %s" % (i, len(symbols), sym, str(ex)[:90]))
        time.sleep(0.35)          # be polite to the upstream
    log("%s: %d/%d fetched" % (label, len(rows), len(symbols)))
    return rows


def slim(r):
    return {"t": r["ticker"], "p": r.get("price"), "c": r.get("day_change_pct"),
            "s": r["score"], "v": r["verdict"]}


def brief(r, cur="$"):
    d = {"t": r["ticker"], "n": r["name"], "p": r.get("price"),
         "c": r.get("day_change_pct"), "s": r["score"]}
    if r.get("upside") is not None:
        d["u"] = round(r["upside"], 1)
    return d


def session_note(us):
    """One factual line about the session, derived from the data."""
    moves = [r for r in us if r.get("day_change_pct") is not None]
    if not moves:
        return "No intraday moves were available for this run."
    moves.sort(key=lambda r: r["day_change_pct"])
    down, up = moves[:3], moves[-3:][::-1]
    bysec = {}
    for r in moves:
        bysec.setdefault(r.get("sector") or "n/a", []).append(r["day_change_pct"])
    ranked = sorted(((s, sum(v) / len(v), len(v)) for s, v in bysec.items() if len(v) >= 2),
                    key=lambda x: x[1])
    parts = []
    if ranked:
        w, wv, _ = ranked[0]
        b, bv, _ = ranked[-1]
        parts.append("%s was the weakest sector (%+.2f%% average) and %s the strongest (%+.2f%%)"
                     % (w, wv, b, bv))
    parts.append("biggest falls %s; biggest gains %s"
                 % (", ".join("%s %+.2f%%" % (r["ticker"], r["day_change_pct"]) for r in down),
                    ", ".join("%s %+.2f%%" % (r["ticker"], r["day_change_pct"]) for r in up)))
    line = "; ".join(parts)
    return (line[:1].upper() + line[1:] + ".") if line else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="fetch and score, write nothing")
    ap.add_argument("--date", help="override run date (YYYY-MM-DD)")
    args = ap.parse_args()

    today = (datetime.date.fromisoformat(args.date) if args.date
             else datetime.datetime.now(datetime.timezone.utc).date())
    stamp = datetime.datetime.now(datetime.timezone.utc)
    label = today.strftime("%a %-d %b %Y") if os.name != "nt" else today.isoformat()
    weekend = today.weekday() >= 5

    failures = []
    log("run %s (%s)" % (today.isoformat(), "weekend/holiday" if weekend else "trading day"))

    log("fetching %d US stocks..." % len(US_STOCKS))
    us_raw = gather(US_STOCKS, fetch_stock, "US", failures)
    log("fetching %d Canadian stocks..." % len(CA_STOCKS))
    # TSX dot notation for share classes (e.g. "TECK.B") maps to a dash on Yahoo
    # Finance ("TECK-B.TO", not "TECK.B.TO" — verified live against the chart API).
    ca_raw = gather([t.replace(".", "-") + ".TO" for t in CA_STOCKS], fetch_stock, "Canada", failures)
    log("fetching %d funds..." % len(FUNDS))
    fu_raw = gather(FUNDS, fetch_fund, "Funds", failures)

    got, want = len(us_raw) + len(ca_raw), len(US_STOCKS) + len(CA_STOCKS)
    if want and got / want < MIN_STOCK_COVERAGE:
        log("ABORT: only %d/%d stocks fetched (< %.0f%%). Nothing written."
            % (got, want, MIN_STOCK_COVERAGE * 100))
        return 1

    us = sorted((evaluate(r) for r in us_raw), key=lambda r: -r["score"])
    ca = sorted((evaluate(r) for r in ca_raw), key=lambda r: -r["score"])
    log("scored %d US, %d CA — top: %s"
        % (len(us), len(ca), ", ".join("%s %.1f" % (r["ticker"], r["score"]) for r in us[:3])))

    captured = stamp.strftime("%d %b %Y, %H:%M UTC")
    meta = {"label": label, "date": today.isoformat(), "captured": captured,
            "status": "Market closed" if weekend else "Latest quotes",
            "failures": failures}

    if args.dry_run:
        log("dry run — nothing written")
        return 0

    # ---- investor chatter (optional — never blocks a run) ----
    universe_tickers = [r["ticker"] for r in us] + [r["ticker"] for r in ca] + [f[0] for f in FUNDS]
    tweets = investor_tweets.fetch(universe_tickers, log=log)
    if tweets:
        log("investor tweets: %d matching mention(s)" % len(tweets))

    # ---- 13F holdings — free, official, no key required ----
    thirteenf_hits = thirteen_f.fetch(us + ca, log=log)
    if thirteenf_hits:
        log("13F holdings: %d matching position(s)" % len(thirteenf_hits))

    # ---- report page ----
    body = render_report.render(us, ca, fu_raw, meta, tweets, thirteenf_hits)
    page = (REPORT_HEAD % {"label": label}) + body + (REPORT_TAIL % STARS_JS)
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    rp = os.path.join(ROOT, "reports", "%s.html" % today.isoformat())
    with open(rp, "w") as f:
        f.write(page)
    log("wrote reports/%s.html (%.0f KB)" % (today.isoformat(), len(page) / 1024))

    # ---- history ----
    hp = os.path.join(ROOT, "data", "history.json")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    hist = []
    if os.path.exists(hp):
        try:
            with open(hp) as f:
                hist = json.load(f) or []
        except json.JSONDecodeError:
            log("history.json unreadable — starting a fresh archive")

    moves = [r["day_change_pct"] for r in us if r.get("day_change_pct") is not None]
    best_ca = next((r for r in ca if not r["guardrails"]), ca[0] if ca else None)
    top_fund = next((f for f in fu_raw if f["ticker"] == "SPUS"),
                    fu_raw[0] if fu_raw else None)

    entry = {
        "date": today.isoformat(), "label": label,
        "session": "closed — last available quotes" if weekend else captured,
        "us_avg": round(sum(moves) / len(moves), 2) if moves else None,
        "counts": {k: len([r for r in us + ca if r["verdict"] == k])
                   for k in ["Strong Buy", "Buy", "Hold", "Wait", "Skip"]},
        "top_us": [brief(r) for r in us[:3]],
        "best_ca": brief(best_ca, "C$") if best_ca else None,
        "top_etf": ({"t": top_fund["ticker"], "n": top_fund["name"],
                     "p": top_fund.get("price"), "c": top_fund.get("day_change_pct")}
                    if top_fund else None),
        "note": session_note(us),
        "us": [slim(r) for r in us],
        "ca": [slim(r) for r in ca],
    }
    hist = [h for h in hist if h.get("date") != entry["date"]]   # re-run replaces
    hist.append(entry)
    hist.sort(key=lambda h: h.get("date", ""))
    with open(hp, "w") as f:
        json.dump(hist, f, indent=1)
    log("history.json now holds %d run(s)" % len(hist))

    # ---- reports page (keep index.html as landing page) ----
    with open(os.path.join(ROOT, "reports.html"), "w") as f:
        f.write(build_site.build_index(hist))
    log("reports.html rebuilt")

    if failures:
        log("NOTE: %d fetch failure(s): %s" % (len(failures), ", ".join(failures)))
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
