#!/usr/bin/env python3
"""Run the Colab notebook and generate ML analysis outputs."""
import json
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime

def create_stub_page():
    """Create a stub ML Analysis page for the first run."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ML Analysis - Halal Market Ledger</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,700&family=JetBrains+Mono:wght@400;500;700&display=swap">
    <link rel="stylesheet" href="assets/style.css">
    <style>
        .ml-container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .nav-tabs { display: flex; gap: 1rem; margin-bottom: 2rem; }
        .nav-tabs a { padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 4px; font-weight: 500; background: #e1e0d9; color: #0b0b0b; }
        .nav-tabs a.active { background: #0b0b0b; color: #fcfcfb; }
        .status-box { background: #e1e0d9; padding: 2rem; border-radius: 6px; text-align: center; margin: 2rem 0; }
    </style>
</head>
<body>
<script>(function(){try{var t=localStorage.getItem('hml-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>

<div class="ml-container">
    <div style="margin-bottom: 3rem;">
        <h1>Machine Learning Analysis</h1>
        <p>AI-powered forecasting, technical indicators & fundamental scores updated daily.</p>
        <div class="nav-tabs">
            <a href="index.html">🏠 Home</a>
            <a href="view-screen.html">📊 View Screen</a>
            <a href="ml-analysis.html" class="active">🤖 ML Analysis</a>
        </div>
    </div>

    <div class="status-box">
        <h2 style="margin-top: 0;">⏳ Initializing ML Analysis</h2>
        <p>The machine learning analysis is being generated for the first time. This typically takes 10-15 minutes.</p>
        <p>The system will run the notebook daily at <strong>13:10 UTC</strong> and update this page automatically.</p>
        <p><small>Check back shortly for results, or <a href="index.html">view the standard reports</a>.</small></p>
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
    with open("ml-analysis.html", "w") as f:
        f.write(html_content)
    print("✓ Stub ML Analysis page created")

def run_notebook():
    """Execute the Colab notebook using nbconvert and papermill."""
    notebook_path = Path("halal_stocks_ml_forecasting.ipynb")
    output_dir = Path("ml_analysis")
    output_dir.mkdir(exist_ok=True)

    if not notebook_path.exists():
        print(f"Error: {notebook_path} not found")
        return False

    print(f"Running notebook: {notebook_path}")

    try:
        subprocess.run(
            ["papermill", str(notebook_path), str(output_dir / "output.ipynb"), "--kernel", "python3"],
            timeout=1200,
            check=True,
            capture_output=False
        )
        print("✓ Notebook executed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Notebook execution failed: {e}")
        return False
    except FileNotFoundError:
        print("Installing papermill...")
        subprocess.run(["pip", "install", "-q", "papermill"], check=True)
        return run_notebook()

def generate_ml_dashboard():
    """Generate HTML dashboard from ML outputs."""
    try:
        # Check if outputs exist
        if not Path("signals.csv").exists():
            print("⚠ signals.csv not found - generating stub page")
            create_stub_page()
            return True

        signals = pd.read_csv("signals.csv")
        fund = pd.read_csv("fundamentals.csv") if Path("fundamentals.csv").exists() else pd.DataFrame()
        metrics = pd.read_csv("validation_metrics.csv") if Path("validation_metrics.csv").exists() else pd.DataFrame()

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ML Analysis - Halal Market Ledger</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,700&family=JetBrains+Mono:wght@400;500;700&display=swap">
    <link rel="stylesheet" href="assets/style.css">
    <style>
        .ml-container {{ max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }}
        .nav-tabs {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
        .nav-tabs a {{ padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 4px; font-weight: 500; background: #e1e0d9; color: #0b0b0b; }}
        .nav-tabs a.active {{ background: #0b0b0b; color: #fcfcfb; }}
        .buy-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin: 2rem 0; }}
        .card {{ background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 6px; padding: 1.5rem; }}
        .card h3 {{ margin: 0 0 0.5rem 0; font-size: 1.2rem; }}
        .card .price {{ font-size: 1.4rem; font-weight: 700; margin: 0.5rem 0; }}
        .card .pred {{ color: #2a78d6; font-weight: 600; }}
        .card .bullish {{ color: #008300; }}
        .card .bearish {{ color: #e34948; }}
        .metrics-table {{ width: 100%; border-collapse: collapse; margin: 2rem 0; }}
        .metrics-table th {{ text-align: left; padding: 0.75rem; background: #e1e0d9; font-weight: 600; border-bottom: 2px solid #0b0b0b; }}
        .metrics-table td {{ padding: 0.75rem; border-bottom: 1px solid #e1e0d9; }}
        .metrics-table tr:hover {{ background: #f5f5f0; }}
        .buy-count {{ font-size: 2rem; font-weight: 700; color: #2a78d6; margin-right: 0.5rem; }}
        @media (prefers-color-scheme: dark) {{
            .card {{ background: #1a1a1a; border-color: #333; }}
            .metrics-table th {{ background: #333; }}
            .metrics-table tr:hover {{ background: #222; }}
        }}
    </style>
</head>
<body>
<script>(function(){{try{{var t=localStorage.getItem('hml-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}}})();</script>

<div class="ml-container">
    <div style="margin-bottom: 3rem;">
        <h1>Machine Learning Analysis</h1>
        <p>AI-powered forecasting, technical indicators & fundamental scores updated daily.</p>
        <div class="nav-tabs">
            <a href="index.html">🏠 Home</a>
            <a href="view-screen.html">📊 View Screen</a>
            <a href="ml-analysis.html" class="active">🤖 ML Analysis</a>
        </div>
    </div>

    <div style="background: #e1e0d9; padding: 1.5rem; border-radius: 6px; margin: 2rem 0;">
        <h2 style="margin-top: 0;">Summary</h2>
        <p><strong>Total BUY signals:</strong> <span class="buy-count">{len(signals[signals['signal'] == 'BUY'])}</span></p>
        <p><strong>WATCH (bullish but unvalidated):</strong> {len(signals[signals['signal'].str.startswith('WATCH')])}</p>
        <p><strong>NO BUY:</strong> {len(signals[signals['signal'] == 'NO BUY'])}</p>
        <p><small>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</small></p>
    </div>

    <h2>🎯 BUY Signals (Validated Edge + Bullish Forecast)</h2>
    <div class="buy-list">
"""

        buy_signals = signals[signals['signal'] == 'BUY'].head(12)
        for _, row in buy_signals.iterrows():
            conf = "█" * int(row.get('confluence', 0)) + "░" * (3 - int(row.get('confluence', 0)))
            html_content += f"""
        <div class="card">
            <h3>{row['ticker']}</h3>
            <div class="price">${row.get('last_close', 'N/A')}</div>
            <div>
                <div><strong>5-Day Forecast:</strong> <span class="pred">{row.get('pred_5d_return_%', 'N/A')}%</span></div>
                <div><strong>Target Price:</strong> ${row.get('pred_price_5d', 'N/A')}</div>
                <div><strong>Confluence:</strong> {conf}</div>
                <div><strong>Technical:</strong> <span class="{'bullish' if row.get('ta_label') == 'Bullish' else 'bearish'}">{row.get('ta_label', 'N/A')}</span></div>
            </div>
        </div>
"""

        html_content += """
    </div>

    <h2>📋 Full Signals Table</h2>
    <table class="metrics-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Last Close</th>
                <th>5D Forecast %</th>
                <th>RSI Daily</th>
                <th>RSI Weekly</th>
                <th>TA Score</th>
                <th>Fundamentals</th>
                <th>Signal</th>
                <th>Confluence</th>
            </tr>
        </thead>
        <tbody>
"""

        for _, row in signals.head(25).iterrows():
            html_content += f"""
            <tr>
                <td><strong>{row['ticker']}</strong></td>
                <td>${row.get('last_close', 'N/A')}</td>
                <td>{row.get('pred_5d_return_%', 'N/A'):+.2f}%</td>
                <td>{row.get('rsi_daily', 'N/A'):.0f}</td>
                <td>{row.get('rsi_weekly', 'N/A'):.0f}</td>
                <td>{row.get('ta_score', 'N/A')}</td>
                <td>{row.get('fund_view', 'N/A')}</td>
                <td>{row['signal']}</td>
                <td>{row.get('confluence', 0)}/3</td>
            </tr>
"""

        html_content += """
        </tbody>
    </table>

    <div style="margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #e1e0d9; color: #52514e; font-size: 0.9rem;">
        <p>
            <strong>Disclaimer:</strong> This is an educational analysis tool combining machine learning forecasts,
            technical indicators, and fundamental ratios. Not investment advice.
            <a href="signals.csv" style="color: #2a78d6;">Download signals.csv</a> ·
            <a href="fundamentals.csv" style="color: #2a78d6;">Download fundamentals.csv</a>
        </p>
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
"""

        with open("ml-analysis.html", "w") as f:
            f.write(html_content)

        print("✓ ML Analysis dashboard generated")
        return True
    except Exception as e:
        print(f"✗ Failed to generate dashboard: {e}")
        return False

def main():
    print("=" * 60)
    print("Halal Market Ledger - ML Analysis Pipeline")
    print("=" * 60)

    # Step 1: Run notebook
    success = run_notebook()
    if not success:
        print("⚠ Notebook execution had issues, attempting to generate dashboard from existing outputs...")

    # Step 2: Generate dashboard (works even if notebook failed)
    if not generate_ml_dashboard():
        print("✗ Failed to generate ML Analysis dashboard")
        return False

    print("\n✓ ML Analysis pipeline completed!")
    return True

if __name__ == "__main__":
    exit(0 if main() else 1)
