#!/usr/bin/env python3
"""
Advanced ML Forecasting with Time Series Models
Includes: ARIMA, SARIMA, XGBoost and an inverse-RMSE weighted ensemble
Generates 5-day forecasts with visualizations
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json
from pathlib import Path

from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    print("[WARN] statsmodels not available - ARIMA/SARIMA disabled")

# Chart styling
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
COLORS = {"arima": "#2a78d6", "sarima": "#eb6834", "xgboost": "#1baf7a",
          "ensemble": "#6250d6", "naive": "#898781", "actual": "#0b0b0b"}
MODELS = ("arima", "sarima", "xgboost", "ensemble")
CHART_DPI = 150

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": MUTED, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2, "font.size": 11, "legend.frameon": False,
})


def _recursive_forecast(model, history, steps, lags):
    """Feed each prediction back in as the newest lag (multi-step, like ARIMA)."""
    window = list(history[-lags:])
    out = []
    for _ in range(steps):
        p = float(model.predict(np.array(window[-lags:]).reshape(1, -1))[0])
        out.append(p)
        window.append(p)
    return np.array(out)


class TimeSeriesForecaster:
    def __init__(self, ticker, close_prices, output_dir="ml_analysis"):
        # newer yfinance returns a one-column DataFrame for a single ticker
        if isinstance(close_prices, pd.DataFrame):
            close_prices = close_prices.iloc[:, 0]
        self.ticker = ticker
        self.close = close_prices.dropna()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.forecasts = {}

    def prepare_data(self, train_ratio=0.8, test_days=30):
        """Split on a positional index for the models; real dates are kept for plotting."""
        self.dates = pd.DatetimeIndex(self.close.index)
        self.series = pd.Series(self.close.to_numpy(dtype=float), index=pd.RangeIndex(len(self.close)))

        split_idx = int(len(self.series) * train_ratio)
        self.train = self.series.iloc[:split_idx]
        self.test = self.series.iloc[split_idx:split_idx + test_days]
        if len(self.test) < 5:
            self.test = self.series.iloc[split_idx:]

        self.naive = self._scores(np.full(len(self.test), self.train.iloc[-1]))
        return len(self.train), len(self.test)

    def _scores(self, test_pred):
        y = self.test.to_numpy()
        pred = np.asarray(test_pred, dtype=float)[:len(y)]
        return {
            'rmse': float(np.sqrt(mean_squared_error(y, pred))),
            'mae': float(mean_absolute_error(y, pred)),
            'r2': float(r2_score(y, pred)),
            'test_pred': pred,
        }

    def _statsmodel(self, fit, name, periods):
        if not HAS_STATSMODELS or len(self.train) < 50:
            return None
        try:
            test_pred = fit(self.train).forecast(steps=len(self.test))
            # refit on the full history so the forecast starts from the latest close
            forecast = fit(self.series).forecast(steps=periods)
            return {'forecast': np.asarray(forecast, dtype=float), 'model': name, **self._scores(test_pred)}
        except Exception as e:
            print(f"  ! {name} failed for {self.ticker}: {str(e)[:50]}")
            return None

    def forecast_arima(self, periods=5):
        return self._statsmodel(lambda s: ARIMA(s, order=(1, 1, 1)).fit(), 'ARIMA(1,1,1)', periods)

    def forecast_sarima(self, periods=5):
        return self._statsmodel(
            lambda s: SARIMAX(s, order=(1, 1, 1), seasonal_order=(1, 0, 1, 5)).fit(disp=False),
            'SARIMA(1,1,1)(1,0,1,5)', periods)

    def forecast_xgboost(self, periods=5, lags=10):
        if len(self.train) < lags + 10:
            return None
        try:
            def fit(values):
                X = np.lib.stride_tricks.sliding_window_view(values[:-1], lags)
                return xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1,
                                        random_state=42, verbosity=0).fit(X, values[lags:])

            train = self.train.to_numpy()
            full = self.series.to_numpy()
            test_pred = _recursive_forecast(fit(train), train, len(self.test), lags)
            forecast = _recursive_forecast(fit(full), full, periods, lags)
            return {'forecast': forecast, 'model': f'XGBoost (lag={lags})', **self._scores(test_pred)}
        except Exception as e:
            print(f"  ! XGBoost failed for {self.ticker}: {str(e)[:50]}")
            return None

    def forecast_ensemble(self):
        members = {m: self.forecasts[m] for m in ('arima', 'sarima', 'xgboost') if self.forecasts.get(m)}
        if not members:
            return None
        inv = np.array([1 / max(f['rmse'], 1e-9) for f in members.values()])
        w = inv / inv.sum()
        forecast = np.average([f['forecast'] for f in members.values()], axis=0, weights=w)
        test_pred = np.average([f['test_pred'] for f in members.values()], axis=0, weights=w)
        return {
            'forecast': forecast,
            'model': f'Ensemble ({len(members)} models, inverse-RMSE weighted)',
            **self._scores(test_pred),
            'weights': {m: float(x) for m, x in zip(members, w)},
        }

    def run_all_models(self, forecast_periods=5):
        print(f"\n  Running models for {self.ticker}...")
        self.prepare_data(test_days=30)
        self.forecasts['arima'] = self.forecast_arima(forecast_periods)
        self.forecasts['sarima'] = self.forecast_sarima(forecast_periods)
        self.forecasts['xgboost'] = self.forecast_xgboost(forecast_periods)
        self.forecasts['ensemble'] = self.forecast_ensemble()
        return self.forecasts

    def _style_dates(self, ax):
        loc = mdates.AutoDateLocator(minticks=4, maxticks=8)
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))

    def generate_forecast_chart(self, lookback=90, zoom=15):
        """Left: recent prices plus the forecast. Right: zoom on the forecast days."""
        models = [m for m in MODELS if self.forecasts.get(m)]
        if not models:
            return None

        last_date, last_close = self.dates[-1], float(self.series.iloc[-1])
        steps = len(self.forecasts[models[0]]['forecast'])
        future = pd.bdate_range(last_date + pd.offsets.BDay(1), periods=steps)

        fig, (ax, zx) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={'width_ratios': [2.2, 1]})
        for a, n in ((ax, lookback), (zx, zoom)):
            a.plot(self.dates[-n:], self.series.to_numpy()[-n:], color=COLORS['actual'], lw=2, label='Actual close')
            a.axvspan(last_date, future[-1], color=GRID, alpha=0.6, lw=0)
            for m in models:
                f = self.forecasts[m]['forecast']
                a.plot([last_date, *future], [last_close, *f], '-o', color=COLORS[m],
                       lw=2.8 if m == 'ensemble' else 1.6, ms=4 if a is ax else 6,
                       label=f"{m.upper()}  ${f[-1]:,.2f}", zorder=3 if m == 'ensemble' else 2)
            self._style_dates(a)
            a.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))

        ax.set_title(f"{self.ticker}: last {lookback} trading days and the next {steps}",
                     loc='left', fontweight='bold')
        zx.set_title(f"Zoom: forecast for {future[0]:%b %d} - {future[-1]:%b %d}", loc='left', fontweight='bold')
        zx.annotate(f"last close ${last_close:,.2f}", (last_date, last_close), xytext=(-8, 10),
                    textcoords='offset points', ha='right', fontsize=9, color=MUTED)
        ax.legend(loc='upper left', fontsize=9.5, title='5th-day forecast', title_fontsize=9.5)
        fig.tight_layout()

        chart_path = self.output_dir / f"{self.ticker}_forecast_chart.png"
        fig.savefig(chart_path, dpi=CHART_DPI)
        plt.close(fig)
        return chart_path.name

    def generate_accuracy_chart(self):
        """Hold-out error of each model next to the naive 'price stays flat' guess (lower is better)."""
        models = [m for m in MODELS if self.forecasts.get(m)]
        if not models:
            return None

        rows = [(m.upper(), self.forecasts[m], COLORS[m]) for m in models] + [('NAIVE', self.naive, COLORS['naive'])]
        names = [r[0] for r in rows]
        colors = [r[2] for r in rows]

        fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
        for a, key, label in ((axes[0], 'rmse', 'RMSE'), (axes[1], 'mae', 'MAE')):
            vals = [r[1][key] for r in rows]
            bars = a.barh(names, vals, color=colors, height=0.6)
            a.bar_label(bars, labels=[f"${v:,.2f}" for v in vals], padding=4, fontsize=10)
            a.axvline(self.naive[key], color=COLORS['naive'], ls='--', lw=1)
            a.set_xlim(0, max(vals) * 1.25)
            a.invert_yaxis()
            a.grid(axis='y', visible=False)
            a.set_title(f"{label} on the last {len(self.test)} held-out days (lower is better)",
                        loc='left', fontweight='bold', fontsize=11)
        fig.suptitle(f"{self.ticker}: dashed line = naive forecast; bars left of it beat naive",
                     x=0.01, ha='left', fontsize=10, color=MUTED)
        fig.tight_layout()

        chart_path = self.output_dir / f"{self.ticker}_accuracy_chart.png"
        fig.savefig(chart_path, dpi=CHART_DPI)
        plt.close(fig)
        return chart_path.name

    def to_dict(self):
        results = {
            'ticker': self.ticker,
            'timestamp': datetime.now().isoformat(),
            'models': {},
            'naive': {k: self.naive[k] for k in ('rmse', 'mae', 'r2')},
        }
        for model_name, forecast_data in self.forecasts.items():
            if forecast_data:
                results['models'][model_name] = {
                    'algorithm': forecast_data['model'],
                    'r2_score': forecast_data.get('r2'),
                    'rmse': forecast_data.get('rmse'),
                    'mae': forecast_data.get('mae'),
                    'forecast_5d': forecast_data['forecast'].tolist()[:5],
                    'weights': forecast_data.get('weights', {}),
                }
        return results


def main():
    """Example usage"""
    import yfinance as yf

    tickers = ["NVDA", "AAPL", "MSFT"]
    output_dir = Path("ml_analysis")
    output_dir.mkdir(exist_ok=True)
    all_results = []

    for ticker in tickers:
        print(f"\n{'='*60}\nProcessing {ticker}\n{'='*60}")
        try:
            close = yf.download(ticker, period="1y", progress=False)['Close']
            forecaster = TimeSeriesForecaster(ticker, close, output_dir)
            forecaster.run_all_models(forecast_periods=5)
            print(f"  [OK] Forecast chart: {forecaster.generate_forecast_chart()}")
            print(f"  [OK] Accuracy chart: {forecaster.generate_accuracy_chart()}")
            results = forecaster.to_dict()
            all_results.append(results)
            for model, data in results['models'].items():
                print(f"    {model.upper():12} R2={data['r2_score']:.3f}  RMSE={data['rmse']:.2f}")
        except Exception as e:
            print(f"  [FAIL] Error: {str(e)[:100]}")

    with open(output_dir / "ml_forecasting_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[OK] Results saved to {output_dir}/ml_forecasting_results.json")


if __name__ == "__main__":
    main()
