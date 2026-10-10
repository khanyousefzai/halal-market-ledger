# GitHub Setup Checklist

Ensure these settings are configured in your GitHub repository for the daily pipeline to work correctly.

## 1. ✅ Repository Visibility

**Settings** → **General** → *Danger Zone*

- [ ] Repository is **PUBLIC** (required for GitHub Pages on free account)
- [ ] If private, upgrade to paid GitHub plan for Pages to work

## 2. ✅ GitHub Pages Configuration

**Settings** → **Pages**

- [ ] **Build and deployment** → Source: **GitHub Actions** (NOT "Deploy from a branch")
- [ ] Custom domain: Leave blank (using `khanyousefzai.github.io`)
- [ ] HTTPS: Should be enforced automatically

## 3. ✅ Actions Permissions

**Settings** → **Actions** → **General**

- [ ] **Workflow permissions**: Set to **Read and write permissions**
  - This allows the daily workflow to commit and push changes
  - Without this, the workflow fails with 403 error

## 4. ✅ Secrets & Environment Variables

**Settings** → **Secrets and variables** → **Actions**

- [ ] `X_BEARER_TOKEN` — (Optional) Twitter API bearer token for investor tweets
  - If not set, investor_tweets.py silently skips
  - To add: Click "New repository secret"

## 5. ✅ Branch Configuration

**Settings** → **General** → *Default branch*

- [ ] Default branch is `main` (or `master`, just make sure it matches `.github/workflows/daily.yml`)
- [ ] The workflow automatically commits to the default branch

## 6. ✅ Deployment Status

**Your repository** → **Actions** tab

- [ ] Click **"Daily report"** workflow
- [ ] Click **"Run workflow"** button
- [ ] Watch for green checkmark (success) or red X (failure)
- [ ] First run takes ~20 minutes (downloads data, trains models)
- [ ] Subsequent runs take ~3-4 minutes

## 7. ✅ Verify Live Site

After successful workflow run:

- [ ] Visit **https://khanyousefzai.github.io/halal-market-ledger/**
- [ ] Should show landing page with two buttons: "View Screen" & "ML Analysis"
- [ ] Click "View Screen" → See daily reports
- [ ] Click "ML Analysis" → See ML forecasting dashboard
- [ ] Both pages should be updated with latest data

---

## Troubleshooting

### Workflow Fails with 403 Error
**Fix:** Settings → Actions → General → Set to **Read and write permissions**

### GitHub Pages Not Deploying
**Fix:** Settings → Pages → Source must be **GitHub Actions** (not "Deploy from a branch")

### Notebook Execution Times Out
**Fix:** This is normal for the first run. ML notebook takes 15-20 minutes because:
- Downloads 3 years of historical data for 50+ stocks
- Trains 3 machine learning models
- Computes technical indicators on 750+ trading days

Subsequent runs use incremental data and are much faster (~1-2 minutes).

### "No such kernel" Error
**Fix:** Already fixed in `requirements.txt` - includes `ipykernel` which registers the kernel automatically.

---

## File Structure After First Successful Run

```
✓ index.html                          (Landing page - choice between two views)
✓ view-screen.html                    (Daily reports page)
✓ ml-analysis.html                    (ML forecasting dashboard - UPDATED)
✓ reports/2026-10-09.html             (Today's report)
✓ data/history.json                   (Updated with today's data)
✓ signals.csv                         (ML signals - UPDATED)
✓ fundamentals.csv                    (Financial ratios - UPDATED)
✓ validation_metrics.csv              (Model performance - UPDATED)
✓ technical_snapshot.csv              (Technical indicators - UPDATED)
✓ .github/workflows/daily.yml         (Workflow schedule & steps)
```

---

## Manual Triggers

Instead of waiting for 13:10 UTC daily run, you can trigger manually:

1. Go to **Actions** tab in your repository
2. Select **"Daily report"** from the list
3. Click **"Run workflow"** button
4. Set **dry_run** to `false` (unless testing)
5. Click **"Run workflow"** green button
6. Watch the execution in real-time

**Expected timeline:**
- ~2 min: Install dependencies
- ~15 min: ML notebook execution (first time)
- ~1 min: Generate ML dashboard
- ~1 min: Commit & deploy

---

## Cron Schedule

Current schedule: `10 13 * * *` (daily at 13:10 UTC)

To change:
1. Edit `.github/workflows/daily.yml`
2. Modify `cron: '10 13 * * *'`
3. Cron format: `minute hour day-of-month month day-of-week`

Examples:
- `'0 9 * * 1-5'` → 09:00 UTC on weekdays only
- `'30 16 * * *'` → 16:30 UTC daily
- `'0 0 * * *'` → Midnight UTC daily

---

## Success Indicators

✅ **You're all set when:**
1. First workflow run completes (green checkmark in Actions)
2. All three pages are live:
   - Landing page (index.html)
   - View Screen (view-screen.html)
   - ML Analysis (ml-analysis.html)
3. CSV files updated with latest data
4. Page updates appear on GitHub Pages within 2-3 minutes of workflow completion

**Enjoy your automated ML-powered equity analysis! 🚀**
