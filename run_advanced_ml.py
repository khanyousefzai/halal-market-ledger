#!/usr/bin/env python3
"""
Weekly ML forecasting: ARIMA, SARIMA, XGBoost and an ensemble for a fixed set of
stocks, each scored by a rolling backtest against the naive forecast. Writes the
charts and results to ml_analysis/ and the page to ml-analysis.html.
"""

import html
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from joblib import Parallel, delayed

warnings.filterwarnings('ignore')

from ml_forecasting_advanced import (TimeSeriesForecaster, HORIZON, BT_ORIGINS, BT_STEP,
                                     TRAIN_WINDOW, MODELS, LABELS, COLORS)

TICKERS = ["NVDA", "MU", "SNDK", "GOOGL", "AAPL", "MSFT", "AMD", "ASML", "TSLA", "CRWD"]
HISTORY = "3y"
OUTPUT_DIR = Path("ml_analysis")


def download(tickers):
    raw = yf.download(tickers, period=HISTORY, auto_adjust=True, progress=False, threads=True)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(tickers[0])
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    return raw


def run_one(ticker, close):
    try:
        return TimeSeriesForecaster(ticker, close, OUTPUT_DIR).run(), None
    except Exception as e:
        return None, f"{ticker}: {str(e)[:80]}"


def run_advanced_forecasting(tickers=TICKERS):
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("=" * 70 + "\nWeekly ML forecasting + backtest\n" + "=" * 70)

    prices = download(tickers)
    jobs = [(t, prices[t].dropna()) for t in tickers if t in prices and prices[t].notna().any()]
    failures = [f"{t}: no price data" for t in tickers if t not in dict(jobs)]

    done = Parallel(n_jobs=-1)(delayed(run_one)(t, c) for t, c in jobs)

    results = []
    for forecaster, err in done:
        if err:
            failures.append(err)
            print(f"  [ERROR] {err}")
            continue
        forecaster.generate_forecast_chart()
        forecaster.generate_accuracy_chart()
        r = forecaster.to_dict()
        results.append(r)
        print(f"  [OK] {r['ticker']}: best vs naive = {LABELS.get(r['best_model'], '-')} "
              f"({r['best_skill']:+.1f}%), {r['backtest']['origins']} backtest dates")

    payload = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "failures": failures, "stocks": results}
    with open(OUTPUT_DIR / "ml_forecasting_results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\n[OK] {len(results)} stocks, {len(failures)} failure(s)")
    return payload


def fmt_pct(v, signed=False, digits=1):
    if v is None:
        return "n/a"
    return f"{v:+.{digits}f}%" if signed else f"{v:.{digits}f}%"


def overall_table(stocks):
    rows = []
    for m in MODELS:
        skills = [s["models"][m]["skill_vs_naive"] for s in stocks if m in s["models"]]
        dirs = [s["models"][m]["dir_acc"] for s in stocks if m in s["models"] and s["models"][m]["dir_acc"] is not None]
        if not skills:
            continue
        rows.append((m, float(np.mean(skills)), sum(x > 0 for x in skills), len(skills),
                     float(np.mean(dirs)) if dirs else None))
    up = float(np.mean([s["backtest"]["up_share"] for s in stocks]))
    return rows, up


def verdict(rows):
    best = max(rows, key=lambda r: r[1])
    if best[1] <= 0:
        return (f"<strong>No model beat the naive forecast on average.</strong> Across these stocks, "
                f"simply assuming the price stays where it is was at least as accurate as every model. "
                f"Treat the forecasts below as illustrations, not trading signals.")
    return (f"<strong>{LABELS[best[0]]} beat the naive forecast by {best[1]:.1f}% on average</strong> "
            f"(on {best[2]} of {best[3]} stocks). That edge is small and measured on one period only.")


def generate_enhanced_dashboard(payload):
    stocks = sorted(payload["stocks"], key=lambda s: s["best_skill"] if s["best_skill"] is not None else -1e9,
                    reverse=True)
    e = html.escape
    generated = datetime.fromisoformat(payload["generated"]).strftime("%a %d %b %Y, %H:%M UTC")

    parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ML Forecasts - Halal Market Ledger</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#129302;</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,700&family=JetBrains+Mono:wght@400;500;700&display=swap">
<link rel="stylesheet" href="assets/style.css">
<style>
  .ml-container {{ max-width: 1200px; margin: 2rem auto; padding: 0 16px; }}
  .nav-tabs {{ display: flex; gap: .75rem; margin: 1rem 0 2rem; flex-wrap: wrap; }}
  .nav-tabs a {{ padding: .6rem 1.2rem; text-decoration: none; border-radius: 4px; font-weight: 500; background: #e1e0d9; color: #0b0b0b; }}
  .nav-tabs a.active {{ background: #0b0b0b; color: #fcfcfb; }}
  .panel {{ background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 6px; padding: 1.25rem 1.5rem; margin: 1.5rem 0; }}
  .verdict {{ border-left: 4px solid #6250d6; }}
  .tbl-wrap {{ overflow-x: auto; }}
  table.ml {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
  table.ml th, table.ml td {{ text-align: right; padding: .45rem .6rem; border-bottom: 1px solid #e1e0d9; white-space: nowrap; }}
  table.ml th:first-child, table.ml td:first-child {{ text-align: left; }}
  table.ml th {{ font-weight: 600; color: #52514e; font-size: .82rem; }}
  .dot {{ display: inline-block; width: .7em; height: .7em; border-radius: 50%; margin-right: .45em; vertical-align: baseline; }}
  .good {{ color: #008300; font-weight: 600; }}
  .bad {{ color: #b3261e; font-weight: 600; }}
  .muted {{ color: #52514e; font-size: .9rem; }}
  .stock-head {{ display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: .5rem; }}
  .stock-head h3 {{ margin: 0; }}
  .chart-img {{ width: 100%; height: auto; border-radius: 4px; margin-top: 1rem; display: block; }}
  .warn {{ background: #fff4e5; border: 1px solid #f0c27b; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) .panel {{ background: #1a1a1a; border-color: #333; }}
    :root:not([data-theme="light"]) .warn {{ background: #2a2116; border-color: #6b5225; }}
  }}
  :root[data-theme="dark"] .panel {{ background: #1a1a1a; border-color: #333; }}
  :root[data-theme="dark"] .warn {{ background: #2a2116; border-color: #6b5225; }}
</style>
</head>
<body>
<script>(function(){{try{{var t=localStorage.getItem('hml-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}}})();</script>
<div class="ml-container">
<h1>ML Forecasts</h1>
<p class="muted">{HORIZON}-day price forecasts from ARIMA, SARIMA, XGBoost and their average, each tested against
the naive forecast (price stays at today's close). Updated weekly &middot; {e(generated)}</p>
<div class="nav-tabs">
  <a href="index.html">Home</a>
  <a href="view-screen.html">View Screen</a>
  <a href="ml-analysis.html" class="active">ML Analysis</a>
</div>
"""]

    if stocks:
        rows, up = overall_table(stocks)
        parts.append(f'<div class="panel verdict"><h2 style="margin-top:0">How much to trust these forecasts</h2>'
                     f'<p>{verdict(rows)}</p><div class="tbl-wrap"><table class="ml"><tr><th>Model</th>'
                     f'<th>Avg error vs naive</th><th>Stocks where it beat naive</th><th>Direction right</th></tr>')
        for m, skill, wins, n, d in rows:
            cls = "good" if skill > 0 else "bad"
            parts.append(f'<tr><td><span class="dot" style="background:{COLORS[m]}"></span>{LABELS[m]}</td>'
                         f'<td class="{cls}">{fmt_pct(skill, signed=True)}</td><td>{wins} of {n}</td>'
                         f'<td>{fmt_pct(d, digits=0)}</td></tr>')
        parts.append(f'</table></div><p class="muted">"Avg error vs naive": positive means smaller errors than '
                     f'assuming no change. Direction: the stocks rose over {HORIZON} days in {up:.0f}% of test '
                     f'windows, so guessing "up" every time scores {up:.0f}%; a model must beat that, not 50%.</p></div>')

    if payload["failures"]:
        items = "".join(f"<li>{e(f)}</li>" for f in payload["failures"])
        parts.append(f'<div class="panel warn"><strong>Not included this week:</strong><ul>{items}</ul></div>')

    for s in stocks:
        t = e(s["ticker"])
        bt = s["backtest"]
        parts.append(f'<div class="panel"><div class="stock-head"><h3>{t}</h3>'
                     f'<span class="muted">last close ${s["last_close"]:,.2f} on {s["last_date"]} &middot; '
                     f'forecast for {s["forecast_dates"][0]} to {s["forecast_dates"][-1]}</span></div>'
                     f'<div class="tbl-wrap"><table class="ml"><tr><th>Model</th><th>Day-{HORIZON} forecast</th>'
                     f'<th>Change</th><th>Backtest error</th><th>vs naive</th><th>Direction right</th></tr>')
        for m in (*MODELS, "naive"):
            d = s["models"].get(m)
            if not d:
                continue
            fc = d["forecast"]
            price = f"${fc[-1]:,.2f}" if fc else "n/a"
            chg = fmt_pct((fc[-1] / s["last_close"] - 1) * 100, signed=True) if fc else "n/a"
            if m == "naive":
                vs, cls = "baseline", ""
            else:
                vs, cls = fmt_pct(d["skill_vs_naive"], signed=True), "good" if d["skill_vs_naive"] > 0 else "bad"
            dir_txt = "-" if d["dir_acc"] is None else f'{d["dir_acc"]:.0f}% <span class="muted">(up: {bt["up_share"]:.0f}%)</span>'
            parts.append(f'<tr><td><span class="dot" style="background:{COLORS[m]}"></span>{d["label"]}</td>'
                         f'<td>{price}</td><td>{chg}</td><td>{fmt_pct(d["mape"], digits=2)}</td>'
                         f'<td class="{cls}">{vs}</td><td>{dir_txt}</td></tr>')
        parts.append('</table></div>')
        if s["failed_models"]:
            parts.append(f'<p class="muted">Model(s) that failed this week: {e(", ".join(s["failed_models"]))}</p>')
        parts.append(f'<img src="ml_analysis/{t}_forecast_chart.png" alt="{t} price and {HORIZON}-day forecasts" class="chart-img" loading="lazy">'
                     f'<img src="ml_analysis/{t}_accuracy_chart.png" alt="{t} backtest scorecard" class="chart-img" loading="lazy">'
                     f'<p class="muted">Backtest: {bt["origins"]} forecasts made between {bt["first"]} and {bt["last"]}, '
                     f'each using only data available on that day.</p></div>')

    parts.append(f"""<div class="panel muted">
<p><strong>Method.</strong> {HISTORY[:-1]} years of daily closes from Yahoo Finance (split/dividend adjusted).
At {BT_ORIGINS} past dates, {BT_STEP} trading days apart, every model is fit on the previous {TRAIN_WINDOW} trading days only,
forecasts the next {HORIZON}, and is compared with what actually happened. "Backtest error" is the average absolute % gap
over those {HORIZON} days. XGBoost predicts daily returns from the last 10 returns. The ensemble is a plain average of the
three models. Forecast dates skip weekends and NYSE holidays.</p>
<p><strong>Not investment advice.</strong> Point forecasts only (no confidence ranges). A past edge, or lack of one,
can change in a different market. <a href="ml_analysis/ml_forecasting_results.json">Download results (JSON)</a></p>
</div>
</div>
<button class="themebtn" id="themebtn" type="button" aria-label="Switch colour theme" style="position: fixed; bottom: 2rem; right: 2rem;">Theme</button>
<script>
(function(){{
  var b=document.getElementById('themebtn'); if(!b) return;
  b.addEventListener('click',function(){{
    var de=document.documentElement, cur=de.getAttribute('data-theme');
    if(!cur){{ cur = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light'; }}
    var next = cur==='dark' ? 'light':'dark';
    de.setAttribute('data-theme',next);
    try{{ localStorage.setItem('hml-theme',next); }}catch(e){{}}
  }});
}})();
</script>
</body>
</html>
""")
    return "".join(parts)


def main():
    payload = run_advanced_forecasting()
    if not payload["stocks"]:
        print("\n[FAIL] No results to display")
        return False
    with open("ml-analysis.html", "w", encoding="utf-8") as f:
        f.write(generate_enhanced_dashboard(payload))
    print("[OK] Dashboard generated: ml-analysis.html")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
