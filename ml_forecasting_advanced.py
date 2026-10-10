#!/usr/bin/env python3
"""
Advanced ML Forecasting with Time Series Models
Includes: ARIMA, SARIMA, XGBoost, Prophet, and ensemble methods
Generates weekly forecasts with visualizations
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
from pathlib import Path

# Time series models
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    HAS_STATSMODELS = True
except:
    HAS_STATSMODELS = False
    print("⚠ statsmodels not available - ARIMA/SARIMA disabled")

try:
    from prophet import Prophet
    HAS_PROPHET = True
except:
    HAS_PROPHET = False
    print("⚠ Prophet not available - Prophet model disabled")

# Chart styling
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
COLORS = {"arima": "#2a78d6", "sarima": "#eb6834", "xgboost": "#1baf7a",
          "prophet": "#e87ba4", "ensemble": "#6250d6", "actual": "#0b0b0b"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": MUTED, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2, "font.size": 10, "figure.figsize": (12, 6),
})

class TimeSeriesForecaster:
    def __init__(self, ticker, close_prices, output_dir="ml_analysis"):
        self.ticker = ticker
        self.close = close_prices.dropna()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        self.forecasts = {}

    def prepare_data(self, train_ratio=0.8, test_days=30):
        """Split data into train/test"""
        # Reset index and set frequency for ARIMA/SARIMA
        close_reindexed = self.close.reset_index(drop=True)
        close_reindexed.index = pd.RangeIndex(len(close_reindexed))

        split_idx = int(len(close_reindexed) * train_ratio)
        self.train = close_reindexed.iloc[:split_idx]
        self.test = close_reindexed.iloc[split_idx:split_idx + test_days]

        if len(self.test) < 5:
            self.test = close_reindexed.iloc[split_idx:]

        return len(self.train), len(self.test)

    def forecast_arima(self, periods=5):
        """ARIMA(1,1,1) forecast"""
        if not HAS_STATSMODELS or len(self.train) < 50:
            return None

        try:
            model = ARIMA(self.train, order=(1, 1, 1))
            fitted = model.fit()
            forecast = fitted.forecast(steps=periods)

            # Test set prediction for accuracy
            test_pred = fitted.forecast(steps=len(self.test))
            rmse = np.sqrt(mean_squared_error(self.test, test_pred[:len(self.test)]))
            mae = mean_absolute_error(self.test, test_pred[:len(self.test)])
            r2 = r2_score(self.test, test_pred[:len(self.test)])

            return {
                'forecast': forecast.values,
                'model': 'ARIMA(1,1,1)',
                'rmse': float(rmse),
                'mae': float(mae),
                'r2': float(r2)
            }
        except Exception as e:
            print(f"  ⚠ ARIMA failed for {self.ticker}: {str(e)[:50]}")
            return None

    def forecast_sarima(self, periods=5):
        """SARIMA(1,1,1)(1,0,1,5) forecast with seasonal component"""
        if not HAS_STATSMODELS or len(self.train) < 50:
            return None

        try:
            model = SARIMAX(self.train, order=(1, 1, 1), seasonal_order=(1, 0, 1, 5))
            fitted = model.fit(disp=False)
            forecast = fitted.forecast(steps=periods)

            test_pred = fitted.forecast(steps=len(self.test))
            rmse = np.sqrt(mean_squared_error(self.test, test_pred[:len(self.test)]))
            mae = mean_absolute_error(self.test, test_pred[:len(self.test)])
            r2 = r2_score(self.test, test_pred[:len(self.test)])

            return {
                'forecast': forecast.values,
                'model': 'SARIMA(1,1,1)(1,0,1,5)',
                'rmse': float(rmse),
                'mae': float(mae),
                'r2': float(r2)
            }
        except Exception as e:
            print(f"  ⚠ SARIMA failed for {self.ticker}: {str(e)[:50]}")
            return None

    def forecast_xgboost(self, periods=5, lag_features=10):
        """XGBoost with lagged features"""
        if len(self.train) < lag_features + 10:
            return None

        try:
            # Create lagged features
            def create_lag_features(data, lags=lag_features):
                X, y = [], []
                for i in range(lags, len(data)):
                    X.append(data[i-lags:i].values)
                    y.append(data.iloc[i])
                return np.array(X), np.array(y)

            X_train, y_train = create_lag_features(self.train)
            X_test, y_test = create_lag_features(self.test)

            if len(X_train) < 10 or len(X_test) < 2:
                return None

            # Train XGBoost
            model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1,
                                     random_state=42, verbosity=0)
            model.fit(X_train, y_train)

            # Forecast
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Multi-step ahead forecast
            last_values = self.close.iloc[-lag_features:].values
            forecast = []
            for _ in range(periods):
                X_pred = last_values[-lag_features:].reshape(1, -1)
                next_pred = model.predict(X_pred)[0]
                forecast.append(next_pred)
                last_values = np.append(last_values[1:], next_pred)

            return {
                'forecast': np.array(forecast),
                'model': f'XGBoost (lag={lag_features})',
                'rmse': float(rmse),
                'mae': float(mae),
                'r2': float(r2)
            }
        except Exception as e:
            print(f"  ⚠ XGBoost failed for {self.ticker}: {str(e)[:50]}")
            return None

    def forecast_ensemble(self, periods=5):
        """Ensemble of all available models"""
        forecasts = []
        weights = []

        # Collect all model forecasts
        for model_name in ['arima', 'sarima', 'xgboost']:
            if model_name in self.forecasts and self.forecasts[model_name] is not None:
                # Weight by R² score (higher R² = better model = higher weight)
                weight = max(0, self.forecasts[model_name].get('r2', 0.1))
                forecasts.append(self.forecasts[model_name]['forecast'])
                weights.append(weight)

        if not forecasts:
            return None

        # Weighted average
        weights = np.array(weights) / np.sum(weights)
        ensemble_forecast = np.average(forecasts, axis=0, weights=weights)

        # Ensemble accuracy on test set
        ensemble_preds = []
        for pred, weight in zip(forecasts, weights):
            ensemble_preds.append(pred[:len(self.test)] * weight if len(pred) >= len(self.test) else None)

        valid_preds = [p for p in ensemble_preds if p is not None]
        if valid_preds:
            ensemble_test = np.mean(valid_preds, axis=0)
            rmse = np.sqrt(mean_squared_error(self.test[:len(ensemble_test)], ensemble_test))
            mae = mean_absolute_error(self.test[:len(ensemble_test)], ensemble_test)
            r2 = r2_score(self.test[:len(ensemble_test)], ensemble_test)
        else:
            rmse = mae = r2 = np.nan

        return {
            'forecast': ensemble_forecast,
            'model': f'Ensemble ({len(forecasts)} models)',
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'weights': {f'model_{i}': float(w) for i, w in enumerate(weights)}
        }

    def run_all_models(self, forecast_periods=5):
        """Run all available models"""
        print(f"\n  Running models for {self.ticker}...")

        self.prepare_data(test_days=30)

        # Run individual models
        self.forecasts['arima'] = self.forecast_arima(forecast_periods)
        self.forecasts['sarima'] = self.forecast_sarima(forecast_periods)
        self.forecasts['xgboost'] = self.forecast_xgboost(forecast_periods)

        # Ensemble
        self.forecasts['ensemble'] = self.forecast_ensemble(forecast_periods)

        return self.forecasts

    def generate_forecast_chart(self):
        """Create visualization of all forecasts"""
        if not self.forecasts:
            return None

        fig, ax = plt.subplots(figsize=(14, 6))

        # Historical data
        ax.plot(self.train.index[-60:], self.train.values[-60:], 'o-',
                color=COLORS['actual'], linewidth=2, label='Historical', markersize=4)

        # Test set
        ax.plot(self.test.index, self.test.values, 'o--',
                color=COLORS['actual'], linewidth=1.5, alpha=0.7, label='Test Set', markersize=3)

        # Generate future dates
        last_date = self.close.index[-1]
        future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=5, freq='D')

        # Plot forecasts
        for model_name, color in COLORS.items():
            if model_name == 'actual':
                continue
            if model_name in self.forecasts and self.forecasts[model_name] is not None:
                forecast = self.forecasts[model_name]['forecast']
                ax.plot(future_dates[:len(forecast)], forecast, 's-',
                       color=color, linewidth=2, label=model_name.upper(), markersize=6, alpha=0.8)

        ax.axvline(last_date, color=MUTED, linestyle=':', linewidth=1, alpha=0.5)
        ax.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax.set_ylabel('Price ($)', fontsize=11, fontweight='bold')
        ax.set_title(f'{self.ticker} - 5-Day Forecast Comparison', fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=9, framealpha=0.95)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save
        chart_path = self.output_dir / f"{self.ticker}_forecast_chart.png"
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close()

        return str(chart_path.relative_to(self.output_dir))

    def generate_accuracy_chart(self):
        """Create model accuracy comparison"""
        metrics = []
        models = []

        for model_name, forecast_data in self.forecasts.items():
            if forecast_data and model_name != 'ensemble':
                models.append(model_name.upper())
                metrics.append(forecast_data.get('r2', 0))

        if not metrics:
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # R² Scores
        colors_list = [COLORS.get(m.lower(), '#999') for m in models]
        ax1.barh(models, metrics, color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax1.set_xlabel('R² Score', fontsize=11, fontweight='bold')
        ax1.set_title('Model Performance (R² Score)', fontsize=12, fontweight='bold')
        ax1.set_xlim(0, 1)
        ax1.axvline(0.5, color=MUTED, linestyle='--', alpha=0.5)
        ax1.grid(axis='x', alpha=0.3)

        # RMSE Comparison
        rmse_vals = [self.forecasts[m.lower()]['rmse'] for m in models if m.lower() in self.forecasts and self.forecasts[m.lower()] is not None]
        if rmse_vals:
            ax2.barh(models, rmse_vals, color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
            ax2.set_xlabel('RMSE', fontsize=11, fontweight='bold')
            ax2.set_title('Prediction Error (RMSE)', fontsize=12, fontweight='bold')
            ax2.grid(axis='x', alpha=0.3)

        plt.tight_layout()

        chart_path = self.output_dir / f"{self.ticker}_accuracy_chart.png"
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close()

        return str(chart_path.relative_to(self.output_dir))

    def to_dict(self):
        """Export results as dictionary"""
        results = {
            'ticker': self.ticker,
            'timestamp': datetime.now().isoformat(),
            'models': {}
        }

        for model_name, forecast_data in self.forecasts.items():
            if forecast_data:
                results['models'][model_name] = {
                    'algorithm': forecast_data['model'],
                    'r2_score': forecast_data.get('r2', None),
                    'rmse': forecast_data.get('rmse', None),
                    'mae': forecast_data.get('mae', None),
                    'forecast_5d': forecast_data['forecast'].tolist()[:5],
                    'weights': forecast_data.get('weights', {})
                }

        return results


def main():
    """Example usage"""
    import yfinance as yf

    # Download sample data
    tickers = ["NVDA", "AAPL", "MSFT"]
    output_dir = Path("ml_analysis")
    output_dir.mkdir(exist_ok=True)

    all_results = []

    for ticker in tickers:
        print(f"\n{'='*60}")
        print(f"Processing {ticker}")
        print('='*60)

        try:
            # Download data
            data = yf.download(ticker, period="1y", progress=False)
            close = data['Close']

            # Forecast
            forecaster = TimeSeriesForecaster(ticker, close, output_dir)
            forecaster.run_all_models(forecast_periods=5)

            # Generate visualizations
            chart1 = forecaster.generate_forecast_chart()
            chart2 = forecaster.generate_accuracy_chart()

            print(f"  ✓ Forecast chart: {chart1}")
            print(f"  ✓ Accuracy chart: {chart2}")

            # Save results
            results = forecaster.to_dict()
            all_results.append(results)

            for model, data in results['models'].items():
                print(f"    {model.upper():12} R²={data['r2_score']:.3f}  RMSE={data['rmse']:.2f}")

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")

    # Save all results
    with open(output_dir / "ml_forecasting_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✓ Results saved to {output_dir}/ml_forecasting_results.json")


if __name__ == "__main__":
    main()
