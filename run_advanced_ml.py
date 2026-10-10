#!/usr/bin/env python3
"""
Run advanced ML forecasting with ARIMA, SARIMA, XGBoost, and Ensemble
Generates charts and comprehensive dashboard
"""

import json
import yfinance as yf
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from ml_forecasting_advanced import TimeSeriesForecaster

def run_advanced_forecasting(tickers=None, output_dir="ml_analysis"):
    """Run advanced ML forecasting for multiple stocks"""

    if tickers is None:
        # Use top stocks from the Halal Market Ledger
        tickers = ["NVDA", "MU", "SNDK", "GOOGL", "AAPL", "MSFT", "AMD", "ASML", "TSLA", "CRWD"]

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print("="*70)
    print("Advanced ML Forecasting Pipeline")
    print("="*70)

    all_results = []

    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")

        try:
            # Download data
            data = yf.download(ticker, period="1y", progress=False)
            close = data['Close']

            if len(close) < 50:
                print(f"  ⚠ Insufficient data ({len(close)} days)")
                continue

            # Run forecasting
            forecaster = TimeSeriesForecaster(ticker, close, output_dir)
            forecaster.run_all_models(forecast_periods=5)

            # Generate visualizations
            chart1 = forecaster.generate_forecast_chart()
            chart2 = forecaster.generate_accuracy_chart()

            if chart1:
                print(f"  ✓ Forecast chart")
            if chart2:
                print(f"  ✓ Accuracy chart")

            # Get results
            results = forecaster.to_dict()
            all_results.append(results)

            # Print summary
            best_model = max(
                [(m, d['r2_score']) for m, d in results['models'].items() if d['r2_score']],
                key=lambda x: x[1] if x[1] else -1
            )
            print(f"  ✓ Best model: {best_model[0].upper()} (R²={best_model[1]:.3f})")

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:60]}")

    # Save all results
    results_file = output_dir / "ml_forecasting_results.json"
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✓ Processed {len(all_results)} stocks")
    print(f"✓ Results saved to {results_file}")

    return all_results


def generate_enhanced_dashboard(results):
    """Generate enhanced HTML dashboard with charts"""

    # Group results by R² score
    top_stocks = sorted(results, key=lambda x: max(
        [m['r2_score'] for m in x['models'].values() if m['r2_score']], default=0
    ), reverse=True)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ML Forecasting Dashboard - Halal Market Ledger</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,700&family=JetBrains+Mono:wght@400;500;700&display=swap">
    <link rel="stylesheet" href="assets/style.css">
    <style>
        .ml-container { max-width: 1400px; margin: 2rem auto; padding: 0 1rem; }
        .nav-tabs { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .nav-tabs a { padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 4px; font-weight: 500; background: #e1e0d9; color: #0b0b0b; }
        .nav-tabs a.active { background: #0b0b0b; color: #fcfcfb; }
        .model-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin: 2rem 0; }
        .model-card { background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 6px; padding: 1rem; }
        .model-card h4 { margin: 0 0 0.5rem 0; font-size: 1rem; }
        .metric { display: flex; justify-content: space-between; font-size: 0.9rem; margin: 0.3rem 0; }
        .metric-good { color: #008300; font-weight: 600; }
        .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; margin: 2rem 0; }
        .chart-box { background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 6px; padding: 1rem; }
        .chart-img { width: 100%; height: auto; border-radius: 4px; }
        .stock-section { background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 6px; padding: 1.5rem; margin: 1.5rem 0; }
        @media (prefers-color-scheme: dark) {
            .model-card { background: #1a1a1a; border-color: #333; }
            .chart-box { background: #1a1a1a; border-color: #333; }
            .stock-section { background: #1a1a1a; border-color: #333; }
        }
    </style>
</head>
<body>
<script>(function(){try{var t=localStorage.getItem('hml-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>

<div class="ml-container">
    <div style="margin-bottom: 2rem;">
        <h1>🤖 ML Forecasting Dashboard</h1>
        <p>Advanced time series forecasting with ARIMA, SARIMA, XGBoost & Ensemble</p>
        <div class="nav-tabs">
            <a href="index.html">🏠 Home</a>
            <a href="view-screen.html">📊 View Screen</a>
            <a href="ml-analysis.html" class="active">🤖 ML Analysis</a>
        </div>
    </div>

    <div style="background: #e1e0d9; padding: 1.5rem; border-radius: 6px; margin: 2rem 0;">
        <h2 style="margin-top: 0;">📊 Forecasting Models</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            <div><strong>ARIMA(1,1,1)</strong> - Autoregressive trend model</div>
            <div><strong>SARIMA(1,1,1)(1,0,1,5)</strong> - Seasonal patterns (5-day)</div>
            <div><strong>XGBoost</strong> - Gradient boosting (non-linear)</div>
            <div><strong>🏆 Ensemble</strong> - Weighted average (best performance)</div>
        </div>
    </div>

    <h2>📈 Top Performing Forecasts</h2>
"""

    # Add charts for top stocks
    for stock in top_stocks[:6]:  # Show top 6
        ticker = stock['ticker']
        models = stock['models']

        best_model = max(
            [(m, d['r2_score']) for m, d in models.items() if d['r2_score']],
            key=lambda x: x[1] if x[1] else -1
        )

        html += f"""
    <div class="stock-section">
        <h3>{ticker} - 5-Day Forecast</h3>
        <div class="model-grid">
"""

        # Model cards
        for model_name, model_data in models.items():
            if model_data['r2_score']:
                html += f"""
            <div class="model-card">
                <h4>{model_name.upper()}</h4>
                <div class="metric">
                    <span>R² Score:</span>
                    <span class="metric-good">{model_data['r2_score']:.3f}</span>
                </div>
                <div class="metric">
                    <span>RMSE:</span>
                    <span>${model_data['rmse']:.2f}</span>
                </div>
                <div class="metric">
                    <span>MAE:</span>
                    <span>${model_data['mae']:.2f}</span>
                </div>
                <div class="metric">
                    <span>Forecast (5D):</span>
                    <span style="font-weight: 700;">${model_data['forecast_5d'][-1]:.2f}</span>
                </div>
            </div>
"""

        html += """
        </div>
        <div class="chart-grid">
"""

        # Charts
        forecast_chart = f"{ticker}_forecast_chart.png"
        accuracy_chart = f"{ticker}_accuracy_chart.png"

        html += f"""
            <div class="chart-box">
                <strong>Forecast Comparison</strong>
                <img src="{forecast_chart}" alt="Forecast Chart" class="chart-img" onerror="this.style.display='none'">
            </div>
            <div class="chart-box">
                <strong>Model Accuracy</strong>
                <img src="{accuracy_chart}" alt="Accuracy Chart" class="chart-img" onerror="this.style.display='none'">
            </div>
"""

        html += """
        </div>
    </div>
"""

    html += """
    <div style="margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #e1e0d9; color: #52514e; font-size: 0.9rem;">
        <p>
            <strong>Model Selection:</strong> SARIMA typically outperforms for stocks with seasonal patterns<br>
            <strong>Ensemble Advantage:</strong> Combines all models using R²-weighted averaging for robustness<br>
            <strong>Forecast Horizon:</strong> 5 trading days ahead with 80% confidence intervals<br>
            <a href="ml_forecasting_results.json" style="color: #0b0b0b;">📥 Download detailed results (JSON)</a>
        </p>
    </div>
</div>

<button class="themebtn" id="themebtn" type="button" aria-label="Switch colour theme" style="position: fixed; bottom: 2rem; right: 2rem;">Theme</button>
<script>
(function(){
  var b=document.getElementById('themebtn'); if(!b) return;
  b.addEventListener('click',function(){
    var de=document.documentElement, cur=de.getAttribute('data-theme');
    if(!cur){ cur = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light'; }
    var next = cur==='dark' ? 'light':'dark';
    de.setAttribute('data-theme',next);
    try{ localStorage.setItem('hml-theme',next); }catch(e){}
  });
})();
</script>
</body>
</html>
"""

    return html


def main():
    print("\n" + "="*70)
    print("STARTING ADVANCED ML FORECASTING")
    print("="*70)

    # Run forecasting
    results = run_advanced_forecasting()

    if results:
        # Generate dashboard
        print("\n" + "="*70)
        print("GENERATING DASHBOARD")
        print("="*70)

        html = generate_enhanced_dashboard(results)

        with open("ml-analysis.html", "w") as f:
            f.write(html)

        print("\n✓ Dashboard generated: ml-analysis.html")
        print("✓ All models completed successfully!")
        return True
    else:
        print("\n✗ No results to display")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
