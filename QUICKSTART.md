# PUMA Analytics Pro - Quick Start Guide

## 🚀 Setup (5 Minutes)

### Step 1: Install Python
Ensure you have Python 3.8+ installed:
```bash
python --version
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Generate Sample Data (Optional)
To test with sample data:
```bash
python generate_sample_data.py
```

This creates:
- `sample_transient_1hz.xlsx` - Transient test at 1Hz
- `sample_transient_10hz.xlsx` - Transient test at 10Hz  
- `sample_steady_state.xlsx` - Steady state test
- `sample_baseline.xlsx` - Baseline for comparison

### Step 4: Convert Config to Excel
```bash
python -c "import pandas as pd; pd.read_csv('sample_config.csv').to_excel('sample_config.xlsx', index=False)"
```

Or manually open `sample_config.csv` in Excel and save as `.xlsx`

### Step 5: Launch Application
```bash
streamlit run puma_analyzer_pro.py
```

The app opens automatically at: http://localhost:8501

## 📊 First Analysis (2 Minutes)

1. **Upload Files:**
   - Test Data: `sample_transient_1hz.xlsx`
   - Configuration: `sample_config.xlsx`
   - Baseline (Optional): `sample_baseline.xlsx`

2. **Select Mode:**
   - Choose "Standard Validation"

3. **Run Analysis:**
   - Click "🚀 Run Analysis"
   - Wait 5-10 seconds

4. **Review Results:**
   - Check KPI dashboard
   - Review failed parameters
   - Drill down into specific sensors
   - Export results

## 🔧 Using Your Own Data

### Prepare Test Data
Your Excel file should have:
- **Column 1:** Time (seconds) - header: "Time" or "Timestamp"
- **Column 2-N:** Sensor values - any names (e.g., "EngineSpeed_rpm")

Example structure:
```
Time | EngineSpeed_rpm | CoolantTemp_C | IntakePress_kPa | ...
0    | 1200           | 75            | 120             | ...
1    | 1205           | 75.2          | 122             | ...
```

### Prepare Configuration
Create Excel with columns:
- **Parameter:** Must match column names in test data
- **Min:** Minimum allowed value (optional)
- **Max:** Maximum allowed value (optional)
- **Unit:** Unit of measurement (optional)
- **ROC:** Rate of change limit (optional)
- **MinDuration:** Minimum violation duration in seconds (optional)

Example:
```
Parameter          | Min  | Max  | Unit | ROC | MinDuration
EngineSpeed_rpm    | 600  | 2100 | rpm  |     |
CoolantTemp_C      | 70   | 110  | °C   | 5   | 5
```

### Best Practices
1. **Start Simple:** Begin with basic Min/Max rules
2. **Refine Gradually:** Add ROC and MinDuration as needed
3. **Test First:** Use sample data to validate your configuration
4. **Document:** Keep notes on why you set specific limits

## 💡 Common Use Cases

### Case 1: Quick Validation
**Goal:** Check if test passed all limits
1. Upload test + config
2. Run standard validation
3. Check pass rate in KPI dashboard
4. Export failed parameters only

### Case 2: Root Cause Analysis
**Goal:** Understand why parameters failed
1. Run standard validation
2. Check category breakdown for patterns
3. Use parameter drilldown on failed sensors
4. Review time series for anomalies

### Case 3: Test Comparison
**Goal:** Compare current test vs baseline
1. Upload test + config + baseline
2. Run standard validation
3. Review baseline delta column in summary table
4. Plot multi-sensor comparison with baseline overlay

### Case 4: Multi-Cycle Analysis
**Goal:** Analyze each transient cycle separately
1. Upload transient test + config
2. Select "Multi-Cycle Analysis" mode
3. Set cycle duration (default 1800s)
4. Run analysis
5. Review cycle-by-cycle results

## 🎯 Key Features

### Automatic Detection
- ✅ Test type (Transient vs Steady State)
- ✅ Sampling frequency (1Hz, 3Hz, 10Hz)
- ✅ Sensor categories (Temperature, Pressure, etc.)

### Advanced Filtering
- ✅ Status filters (PASS/WARNING/FAIL)
- ✅ Category filters
- ✅ Search by parameter name
- ✅ Pagination for large result sets

### Visualizations
- ✅ Interactive heatmaps
- ✅ Multi-sensor time series
- ✅ Baseline overlay
- ✅ Category breakdown charts

### Export Formats
- ✅ JSON (complete session data)
- ✅ CSV (summary table)
- ✅ Excel (multi-sheet report)
- ✅ Failed parameters only

## 📝 Validation Rules Explained

### Threshold Validation
Checks if values stay within Min/Max bounds:
```
Min: 70, Max: 110
Value: 75 → PASS
Value: 115 → FAIL
```

### Rate of Change (ROC)
Detects rapid changes between consecutive samples:
```
ROC: 5
Previous: 75, Current: 78 → Change: 3 → PASS
Previous: 75, Current: 82 → Change: 7 → FAIL
```

### Duration Filter
Ignores brief violations (transient spikes):
```
MinDuration: 5 seconds
2-second spike → Ignored (too short)
10-second violation → FAIL (exceeds minimum)
```

### Status Assignment
- **PASS:** No violations, <10% missing data
- **WARNING:** Minor violations (<5%), <10% missing data
- **FAIL:** Violations >5% OR missing data >10%

## 🆘 Troubleshooting

### "Time column not found"
**Fix:** Rename your time column to "Time" or "Timestamp"

### "Parameter X not found"
**Fix:** Check spelling in config matches test data exactly (case-sensitive)

### App is slow
**Fix:** 
- Close other programs
- Reduce number of parameters in config
- Use category filtering

### Can't export
**Fix:**
- Check disk space
- Try different format (CSV instead of Excel)
- Close Excel if file is already open

## 📚 Need Help?

1. **Check README.md** for detailed documentation
2. **Review sample data** to understand expected format
3. **Contact IT support** for installation issues
4. **Provide feedback** for feature requests

## 🎓 Next Steps

Once comfortable with basics:
1. Customize sensor categories in code
2. Add custom validation rules
3. Deploy on network for team access
4. Integrate with test management systems
5. Automate batch processing

---

**Happy Testing! 🔧**

Built for Cummins Engineering | Production-Grade PUMA Analysis
