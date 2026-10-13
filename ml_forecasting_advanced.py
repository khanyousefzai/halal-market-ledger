#!/usr/bin/env python3
"""
5-day price forecasts from ARIMA, SARIMA, XGBoost and an equal-weight ensemble,
each scored with a rolling-origin backtest against the naive forecast
("the price stays at today's close").
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
from pandas.tseries.holiday import (AbstractHolidayCalendar, Holiday, nearest_workday, GoodFriday,
                                    USMartinLutherKingJr, USPresidentsDay, USMemorialDay,
                                    USLaborDay, USThanksgivingDay)
from pandas.tseries.offsets import CustomBusinessDay
import xgboost as xgb

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    print("[WARN] statsmodels not available - ARIMA/SARIMA disabled")

HORIZON = 5           # trading days ahead
BT_ORIGINS = 20       # backtest forecast dates per stock
BT_STEP = 10          # trading days between backtest dates (> HORIZON, so windows do not overlap)
TRAIN_WINDOW = 500    # rolling training window, trading days
TRAIN_MIN = 250       # no backtest date before this much history exists
XGB_LAGS = 10

MODELS = ("arima", "sarima", "xgboost", "ensemble")
LABELS = {"arima": "ARIMA", "sarima": "SARIMA", "xgboost": "XGBoost", "ensemble": "Ensemble", "naive": "Naive"}

INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
COLORS = {"arima": "#2a78d6", "sarima": "#eb6834", "xgboost": "#1baf7a",
          "ensemble": "#6250d6", "naive": "#898781", "actual": "#0b0b0b"}
CHART_DPI = 150

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": MUTED, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2, "font.size": 11, "legend.frameon": False,
})


class NYSECalendar(AbstractHolidayCalendar):
    rules = [
        Holiday("NewYearsDay", month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
        Holiday("IndependenceDay", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


NYSE_DAY = CustomBusinessDay(calendar=NYSECalendar())


def arima_path(hist, h):
    return np.asarray(ARIMA(hist, order=(1, 1, 1)).fit().forecast(h), dtype=float)


def sarima_path(hist, h):
    fit = SARIMAX(hist, order=(1, 1, 1), seasonal_order=(1, 0, 1, 5)).fit(disp=False)
    return np.asarray(fit.forecast(h), dtype=float)


def xgboost_path(hist, h, lags=XGB_LAGS):
    # Model log returns, not prices: trees cannot output values outside their
    # training range, so a price-level model can never forecast a new high.
    r = np.diff(np.log(hist))
    X = np.lib.stride_tricks.sliding_window_view(r[:-1], lags)
    model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1,
                             random_state=42, verbosity=0, n_jobs=1).fit(X, r[lags:])
    window, out = list(r[-lags:]), []
    for _ in range(h):
        p = float(model.predict(np.array(window[-lags:])[None, :])[0])
        out.append(p)
        window.append(p)
    return hist[-1] * np.exp(np.cumsum(out))


FORECASTERS = {"arima": arima_path, "sarima": sarima_path, "xgboost": xgboost_path}
if not HAS_STATSMODELS:
    FORECASTERS = {"xgboost": xgboost_path}


def forecast_all(hist, h):
    """Price paths for every model plus naive. Equal-weight ensemble: weights tuned
    on the scoring data would flatter the ensemble's score."""
    paths = {"naive": np.repeat(hist[-1], h)}
    for name, fn in FORECASTERS.items():
        try:
            paths[name] = fn(hist, h)
        except Exception:
            pass
    members = [paths[m] for m in FORECASTERS if m in paths]
    if members:
        paths["ensemble"] = np.mean(members, axis=0)
    return paths


def _clean(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else x


class TimeSeriesForecaster:
    def __init__(self, ticker, close_prices, output_dir="ml_analysis"):
        # newer yfinance returns a one-column DataFrame for a single ticker
        if isinstance(close_prices, pd.DataFrame):
            close_prices = close_prices.iloc[:, 0]
        self.ticker = ticker
        self.close = close_prices.dropna().astype(float)
        self.close.index = pd.DatetimeIndex(self.close.index).tz_localize(None)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def run(self, horizon=HORIZON):
        v, idx = self.close.to_numpy(), self.close.index
        if len(v) < TRAIN_MIN + horizon + 1:
            raise ValueError(f"only {len(v)} days of history")
        self.horizon = horizon

        last = len(v) - horizon - 1
        rows = []
        for o in range(max(TRAIN_MIN, last - (BT_ORIGINS - 1) * BT_STEP), last + 1, BT_STEP):
            hist, actual = v[max(0, o + 1 - TRAIN_WINDOW): o + 1], v[o + 1: o + 1 + horizon]
            for m, p in forecast_all(hist, horizon).items():
                rows.append({"origin": idx[o], "o": o, "model": m, "path": p,
                             "mape": float(np.mean(np.abs(p - actual) / actual) * 100),
                             "pred_ret": p[-1] / hist[-1] - 1, "real_ret": actual[-1] / hist[-1] - 1})
        self.backtest = pd.DataFrame(rows)

        self.paths = forecast_all(v[-TRAIN_WINDOW:], horizon)
        self.future_dates = pd.date_range(idx[-1] + NYSE_DAY, periods=horizon, freq=NYSE_DAY)
        self.failed = [LABELS[m] for m in FORECASTERS if m not in self.paths]
        self.scores = self._score()
        return self

    def _score(self):
        bt = self.backtest
        naive_mape = bt.loc[bt["model"] == "naive", "mape"].mean()
        scores = {}
        for m, g in bt.groupby("model"):
            scores[m] = {
                "mape": float(g["mape"].mean()),
                "skill": float((1 - g["mape"].mean() / naive_mape) * 100),
                "dir_acc": np.nan if m == "naive"
                else float((np.sign(g["pred_ret"]) == np.sign(g["real_ret"])).mean() * 100),
            }
        naive = bt[bt["model"] == "naive"]
        self.n_origins = len(naive)
        self.up_share = float((naive["real_ret"] > 0).mean() * 100)
        return scores

    def best_model(self):
        ranked = sorted(((m, s["skill"]) for m, s in self.scores.items() if m != "naive"),
                        key=lambda x: x[1], reverse=True)
        return ranked[0] if ranked else (None, np.nan)

    def _style_dates(self, ax):
        loc = mdates.AutoDateLocator(minticks=4, maxticks=8)
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))

    def generate_forecast_chart(self, lookback=90, zoom=15):
        """Left: recent prices plus the forecast. Right: zoom on the forecast days."""
        models = [m for m in MODELS if m in self.paths]
        if not models:
            return None
        dates, values = self.close.index, self.close.to_numpy()
        last_date, last_close = dates[-1], float(values[-1])

        fig, (ax, zx) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [2.2, 1]})
        for a, n in ((ax, lookback), (zx, zoom)):
            a.plot(dates[-n:], values[-n:], color=COLORS["actual"], lw=2, label="Actual close")
            a.axvspan(last_date, self.future_dates[-1], color=GRID, alpha=0.6, lw=0)
            for m in models:
                f = self.paths[m]
                a.plot([last_date, *self.future_dates], [last_close, *f], "-o", color=COLORS[m],
                       lw=2.8 if m == "ensemble" else 1.6, ms=4 if a is ax else 6,
                       label=f"{LABELS[m]}  ${f[-1]:,.2f} ({f[-1] / last_close - 1:+.1%})",
                       zorder=3 if m == "ensemble" else 2)
            self._style_dates(a)
            a.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))

        ax.set_title(f"{self.ticker}: last {lookback} trading days and the next {self.horizon}",
                     loc="left", fontweight="bold")
        zx.set_title(f"Zoom: {self.future_dates[0]:%b %d} - {self.future_dates[-1]:%b %d}",
                     loc="left", fontweight="bold")
        zx.annotate(f"last close ${last_close:,.2f}", (last_date, last_close), xytext=(-8, 10),
                    textcoords="offset points", ha="right", fontsize=9, color=MUTED)
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=len(labels), fontsize=9.5,
                   title=f"Day-{self.horizon} forecast", title_fontsize=9.5)
        fig.tight_layout(rect=(0, 0.12, 1, 1))

        chart_path = self.output_dir / f"{self.ticker}_forecast_chart.png"
        fig.savefig(chart_path, dpi=CHART_DPI)
        plt.close(fig)
        return chart_path.name

    def generate_accuracy_chart(self):
        """Backtest scorecard: error vs naive, and direction hits vs 'always up'."""
        names = [m for m in (*MODELS, "naive") if m in self.scores]
        colors = [COLORS[m] for m in names]
        labels = [LABELS[m] for m in names]

        fig, (a, b) = plt.subplots(1, 2, figsize=(14, 4.5))
        mape = [self.scores[m]["mape"] for m in names]
        bars = a.barh(labels, mape, color=colors, height=0.6)
        a.bar_label(bars, labels=[f"{v:.2f}%" for v in mape], padding=4, fontsize=10)
        a.axvline(self.scores["naive"]["mape"], color=COLORS["naive"], ls="--", lw=1)
        a.set_xlim(0, max(mape) * 1.25)
        a.set_title(f"Average error over {self.horizon} days (lower is better)",
                    loc="left", fontweight="bold", fontsize=11)

        dnames = [m for m in names if m != "naive"]
        acc = [self.scores[m]["dir_acc"] for m in dnames]
        bars = b.barh([LABELS[m] for m in dnames], acc, color=[COLORS[m] for m in dnames], height=0.6)
        b.bar_label(bars, labels=[f"{v:.0f}%" for v in acc], padding=4, fontsize=10)
        b.axvline(self.up_share, color=INK, ls="--", lw=1)
        b.text(self.up_share, -0.7, f" always up: {self.up_share:.0f}%", fontsize=9, color=INK, va="bottom")
        b.set_xlim(0, 100)
        b.set_title("Direction right (beat the dashed line)", loc="left", fontweight="bold", fontsize=11)

        for ax in (a, b):
            ax.invert_yaxis()
            ax.grid(axis="y", visible=False)
        fig.suptitle(f"{self.ticker}: backtest on {self.n_origins} past dates; "
                     f"dashed line on the left = naive forecast", x=0.01, ha="left", fontsize=10, color=MUTED)
        fig.tight_layout()

        chart_path = self.output_dir / f"{self.ticker}_accuracy_chart.png"
        fig.savefig(chart_path, dpi=CHART_DPI)
        plt.close(fig)
        return chart_path.name

    def to_dict(self):
        best, best_skill = self.best_model()
        return {
            "ticker": self.ticker,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "last_close": float(self.close.iloc[-1]),
            "last_date": self.close.index[-1].date().isoformat(),
            "data_start": self.close.index[0].date().isoformat(),
            "horizon": self.horizon,
            "forecast_dates": [d.date().isoformat() for d in self.future_dates],
            "backtest": {"origins": self.n_origins,
                         "first": self.backtest["origin"].min().date().isoformat(),
                         "last": self.backtest["origin"].max().date().isoformat(),
                         "up_share": self.up_share},
            "best_model": best,
            "best_skill": _clean(best_skill),
            "failed_models": self.failed,
            "models": {m: {"label": LABELS[m],
                           "forecast": [float(x) for x in self.paths[m]] if m in self.paths else None,
                           "mape": _clean(s["mape"]), "skill_vs_naive": _clean(s["skill"]),
                           "dir_acc": _clean(s["dir_acc"])}
                       for m, s in self.scores.items()},
        }
