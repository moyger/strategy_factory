# Get Free Alpaca API Keys (2 Minutes)

## Why You Need This

The Temiz strategy needs **1-minute intraday data** for accurate backtesting. We already built the data loader (`data/alpaca_data_loader.py`), but it needs API keys to download data.

**Good news:** Alpaca offers FREE paper trading with full historical 1-minute data!

---

## Step-by-Step Setup (2 Minutes)

### Step 1: Sign Up (30 seconds)

1. Go to https://alpaca.markets
2. Click "Start Paper Trading" (FREE)
3. Sign up with email (no credit card needed)

### Step 2: Get API Keys (30 seconds)

1. Log in to your Alpaca dashboard
2. Click "API Keys" in left sidebar
3. You'll see two keys:
   - **API Key ID** (starts with PK...)
   - **Secret Key** (starts with ...)
4. Click "View" to reveal the secret key
5. **Important:** These are for PAPER TRADING (not real money)

### Step 3: Use Keys (Choose One Method)

#### Method A: Environment Variables (Recommended)

**macOS/Linux:**
```bash
export APCA_API_KEY_ID='your_key_id_here'
export APCA_API_SECRET_KEY='your_secret_key_here'
```

**Windows (PowerShell):**
```powershell
$env:APCA_API_KEY_ID='your_key_id_here'
$env:APCA_API_SECRET_KEY='your_secret_key_here'
```

**Permanent (add to ~/.bashrc or ~/.zshrc):**
```bash
# Alpaca Paper Trading API
export APCA_API_KEY_ID='your_key_id_here'
export APCA_API_SECRET_KEY='your_secret_key_here'
```

#### Method B: Pass Keys Directly

```python
from data.alpaca_data_loader import AlpacaDataLoader

loader = AlpacaDataLoader(
    api_key='your_key_id_here',
    secret_key='your_secret_key_here',
    paper=True
)
```

#### Method C: Interactive Prompt

Just run the backtest script and it will ask for keys:
```bash
python test_temiz_1min_backtest.py
# Script will prompt you to enter keys
```

---

## Verify Setup

Test if keys work:

```python
from data.alpaca_data_loader import AlpacaDataLoader

# Initialize
loader = AlpacaDataLoader(
    api_key='your_key_id',
    secret_key='your_secret_key',
    paper=True
)

# Download test data (GME on famous squeeze day)
bars = loader.get_1min_bars('GME', '2021-01-28', '2021-01-28')

print(f"✅ Downloaded {len(bars)} 1-minute bars for GME")
print(bars.head())
```

**Expected output:**
```
✅ Alpaca data loader initialized (PAPER mode)
✅ Downloaded 390 1-minute bars for GME

   timestamp            open    high     low   close    volume
0  2021-01-28 09:30:00  265.00  354.83  265.00  354.83  21262000
1  2021-01-28 09:31:00  353.40  368.00  350.63  359.00  4526100
...
```

---

## What Data is Available

### Historical Data (FREE)
- **Bars:** 1-minute, 5-minute, 15-minute, 1-hour, daily
- **History:** Up to 5 years (varies by stock)
- **Assets:** All US stocks, ETFs
- **Extended Hours:** Pre-market (4:00-9:30 AM) and after-hours (4:00-8:00 PM)

### Rate Limits
- **Paper Account:** Essentially unlimited for backtesting
- **Concurrent Requests:** 200/minute
- **Data Points:** No limit

---

## Troubleshooting

### Error: "Authentication failed"
- Check keys are copied correctly (no extra spaces)
- Make sure you're using PAPER trading keys (not live)
- Keys are case-sensitive

### Error: "No data returned"
- Stock may not exist on that date (delisted, too old, etc.)
- Check date format: 'YYYY-MM-DD'
- Some stocks only have data from 2020+

### Error: "alpaca-trade-api not installed"
```bash
pip install alpaca-trade-api
```

### Error: "Rate limit exceeded"
- Slow down requests (add delays between symbols)
- Use batch downloads (`get_multiple_symbols`)

---

## Security Notes

**IMPORTANT:**
- These are PAPER TRADING keys (not real money)
- Still, keep them private (don't commit to Git)
- Add to `.gitignore` if storing in files
- Regenerate keys if accidentally exposed

**Best Practice:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "alpaca_keys.txt" >> .gitignore

# Store keys in .env file (never commit this)
echo "APCA_API_KEY_ID=your_key" > .env
echo "APCA_API_SECRET_KEY=your_secret" >> .env
```

---

## Next Steps

Once you have keys set up:

1. **Run 1-minute backtest:**
   ```bash
   python test_temiz_1min_backtest.py
   ```

2. **Download data for specific stocks:**
   ```python
   from data.alpaca_data_loader import AlpacaDataLoader

   loader = AlpacaDataLoader(paper=True)  # Uses env vars

   # Download GME squeeze day
   gme = loader.get_1min_bars('GME', '2021-01-28', '2021-01-28')

   # Download multiple stocks
   data = loader.get_multiple_symbols(
       ['GME', 'AMC', 'TSLA'],
       '2024-01-01',
       '2024-01-31'
   )
   ```

3. **Run full backtest with filters:**
   ```bash
   python examples/temiz_with_confluence_filters.py
   ```

---

## Alternative: No API Keys?

If you don't want to get Alpaca keys, you can still:

1. **Run daily backtest** (already done - showed +17% return):
   ```bash
   python test_temiz_backtest.py
   ```

2. **Use sample data** (we can create synthetic 1-min data for testing)

3. **Manual testing** (find parabolic stocks, analyze by hand)

But for PROPER validation, 1-minute data is essential!

---

## Resources

- Alpaca Docs: https://alpaca.markets/docs/
- API Reference: https://alpaca.markets/docs/api-references/
- Python SDK: https://github.com/alpacahq/alpaca-trade-api-python

---

**Total Time to Setup:** ~2 minutes

**Cost:** $0 (completely free)

**Value:** Access to 5 years of 1-minute historical data for all US stocks! 🎉
