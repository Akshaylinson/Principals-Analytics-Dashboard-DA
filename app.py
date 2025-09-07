
import os
import math
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
import numpy as np
from scipy import stats

APP_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_NAME = "Principals 14180.xlsx"
EXCEL_PATH = os.path.join(APP_DIR, EXCEL_NAME)

app = Flask(__name__, static_folder="static", template_folder="templates")

# -------------------------
# Load dataset (safe)
# -------------------------
if os.path.exists(EXCEL_PATH):
    try:
        # read using openpyxl engine
        df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
        # normalize column names
        df.columns = [str(c).strip() for c in df.columns]
        print(f"Loaded dataset: {EXCEL_PATH}  ({len(df)} rows, {len(df.columns)} cols)")
    except Exception as e:
        print("Error reading Excel:", e)
        df = pd.DataFrame()
else:
    print(f"⚠️ Excel not found at {EXCEL_PATH} — starting with empty DataFrame.")
    df = pd.DataFrame()

# Helpful col detection (best-effort)
def _find_col(keywords):
    if df.empty: 
        return None
    low = [c.lower() for c in df.columns]
    for kw in keywords:
        for i, name in enumerate(low):
            if kw in name:
                return df.columns[i]
    return None

col_name = _find_col(["name", "principal", "owner"]) or (df.columns[0] if not df.empty else None)
col_city = _find_col(["city", "town"])
col_state = _find_col(["state", "province", "region"])
col_phone = _find_col(["phone", "mobile", "contact", "telephone"])
col_date = _find_col(["date", "created", "registered", "joined"])  # optional

# Precompute a cached CSV (optional) — helpful for fast reloads
CACHE_CSV = os.path.join(APP_DIR, "principals_cache.csv")
if df is not None and not df.empty:
    try:
        df.to_csv(CACHE_CSV, index=False)
    except Exception:
        pass

# -------------------------
# Utility helpers
# -------------------------
def safe_int(x):
    try:
        return int(x)
    except Exception:
        return 0

def get_summary():
    if df is None or df.empty:
        return {
            "total_records": 0,
            "unique_cities": 0,
            "unique_states": 0,
            "unique_principals": 0,
            "phones_present": 0,
            "phones_missing": 0,
            "potential_duplicates": 0,
            "completeness_score": 0,
            "data_quality_score": 0
        }

    total = len(df)
    unique_cities = int(df[col_city].nunique()) if col_city in df.columns else 0
    unique_states = int(df[col_state].nunique()) if col_state in df.columns else 0
    unique_principals = int(df[col_name].nunique()) if col_name in df.columns else 0
    phones_present = int(df[col_phone].notna().sum()) if col_phone in df.columns else 0
    phones_missing = total - phones_present
    
    # Calculate completeness score (0-100)
    completeness_score = 0
    if total > 0:
        completeness_factors = []
        if col_name in df.columns: completeness_factors.append(df[col_name].notna().mean())
        if col_city in df.columns: completeness_factors.append(df[col_city].notna().mean())
        if col_state in df.columns: completeness_factors.append(df[col_state].notna().mean())
        if col_phone in df.columns: completeness_factors.append(df[col_phone].notna().mean())
        if completeness_factors:
            completeness_score = round(sum(completeness_factors) / len(completeness_factors) * 100, 1)
    
    # Calculate data quality score (0-100)
    data_quality_score = 0
    if total > 0:
        quality_factors = []
        # Completeness factor
        quality_factors.append(completeness_score / 100)
        
        # Uniqueness factor
        if col_name in df.columns:
            uniqueness = df[col_name].nunique() / total
            quality_factors.append(min(uniqueness * 1.5, 1.0))  # Scale to value uniqueness
        
        # Consistency factor (check if state values are consistent)
        if col_state in df.columns:
            state_consistency = 1.0  # Default
            state_sample = df[col_state].dropna().head(100)
            if len(state_sample) > 5:
                # Check if values seem consistent (not too many unique values in sample)
                unique_ratio = state_sample.nunique() / len(state_sample)
                state_consistency = 1.0 - min(unique_ratio, 0.5) * 2  # Convert to 0-1 scale
            quality_factors.append(state_consistency)
        
        data_quality_score = round(sum(quality_factors) / len(quality_factors) * 100, 1)

    # potential duplicates: identical normalized name + city + state
    dup_count = 0
    try:
        subset_cols = [c for c in [col_name, col_city, col_state] if c is not None]
        if subset_cols:
            dup_mask = df.duplicated(subset=subset_cols, keep=False)
            dup_count = int(dup_mask.sum())
    except Exception:
        dup_count = 0

    return {
        "total_records": int(total),
        "unique_cities": int(unique_cities),
        "unique_states": int(unique_states),
        "unique_principals": int(unique_principals),
        "phones_present": int(phones_present),
        "phones_missing": int(phones_missing),
        "potential_duplicates": int(dup_count),
        "completeness_score": completeness_score,
        "data_quality_score": data_quality_score
    }

# -------------------------
# Routes / APIs
# -------------------------
@app.route("/")
def index():
    # serve single-page dashboard (index.html) inside templates/
    return render_template("index.html")


@app.route("/api/summary")
def api_summary():
    """Return KPI summary."""
    return jsonify(get_summary())


@app.route("/api/top-states")
def api_top_states():
    """Top states by count. Query param: ?limit=12"""
    if df is None or df.empty or col_state not in df.columns:
        return jsonify([])
    limit = int(request.args.get("limit", 12))
    counts = df[col_state].fillna("Unknown").value_counts().head(limit)
    out = [{"State": s, "count": int(c)} for s, c in counts.items()]
    return jsonify(out)


@app.route("/api/top-cities")
def api_top_cities():
    """Top cities by count. Query param: ?limit=20"""
    if df is None or df.empty or col_city not in df.columns:
        return jsonify([])
    limit = int(request.args.get("limit", 20))
    counts = df[col_city].fillna("Unknown").value_counts().head(limit)
    out = [{"City": s, "count": int(c), "State": None} for s, c in counts.items()]
    # optional: attach top state for city if available
    if col_state in df.columns:
        city_state = (df[[col_city, col_state]]
                      .groupby(col_city)[col_state]
                      .agg(lambda x: x.value_counts().index[0] if len(x) else None))
        for row in out:
            row["State"] = city_state.get(row["City"], None)
    return jsonify(out)


@app.route("/api/phones-by-state")
def api_phones_by_state():
    """Return phones present / total by state (top N states)."""
    if df is None or df.empty or col_state not in df.columns:
        return jsonify([])
    limit = int(request.args.get("limit", 12))
    tmp = df[[col_state, col_phone]] if col_phone in df.columns else df[[col_state]].assign(**{col_phone: pd.NA})
    tmp = tmp.fillna({col_state: "Unknown"})
    grouped = tmp.groupby(col_state).agg(total=(col_state, "count"),
                                        with_phone=(col_phone, lambda s: s.notna().sum() if col_phone in tmp.columns else 0))
    grouped = grouped.sort_values("total", ascending=False).head(limit).reset_index()
    out = [{"State": row[col_state],
            "total": int(row["total"]),
            "with_phone": int(row["with_phone"]),
            "rate": float(row["with_phone"] / row["total"]) if row["total"] else 0.0}
           for idx, row in grouped.iterrows()]
    return jsonify(out)


@app.route("/api/treemap-states")
def api_treemap_states():
    """Return list of {State, count} suitable for treemap."""
    if df is None or df.empty or col_state not in df.columns:
        return jsonify([])
    counts = df[col_state].fillna("Unknown").value_counts()
    out = [{"State": s, "count": int(c)} for s, c in counts.items()]
    return jsonify(out)


@app.route("/api/state-city-heatmap")
def api_state_city_heatmap():
    """
    Builds a heatmap matrix: x = top N states, y = top M cities overall,
    z = counts for each (state, city).
    Query params: states=10, cities=15
    """
    if df is None or df.empty or col_state not in df.columns or col_city not in df.columns:
        return jsonify({"states": [], "cities": [], "z": []})

    n_states = int(request.args.get("states", 10))
    n_cities = int(request.args.get("cities", 15))

    top_states = df[col_state].fillna("Unknown").value_counts().head(n_states).index.tolist()
    top_cities = df[col_city].fillna("Unknown").value_counts().head(n_cities).index.tolist()

    # build matrix
    z = []
    for c in top_cities:
        row = []
        for s in top_states:
            mask = (df[col_city].fillna("Unknown") == c) & (df[col_state].fillna("Unknown") == s)
            row.append(int(mask.sum()))
        z.append(row)

    return jsonify({"states": top_states, "cities": top_cities, "z": z})


@app.route("/api/table")
def api_table():
    """
    Server-side table for DataTables-like frontend.
    Accepts:
      - start (offset)
      - length (page size)
      - search[value] (global search)
      - order[0][column] (sort column index)
      - order[0][dir] (sort direction)
    Returns:
      {recordsTotal, recordsFiltered, data: [ {col: val, ...}, ... ] }
    """
    if df is None or df.empty:
        return jsonify({"recordsTotal": 0, "recordsFiltered": 0, "data": []})

    try:
        start = int(request.args.get("start", 0))
        length = int(request.args.get("length", 25))
    except Exception:
        start, length = 0, 25

    search = request.args.get("search[value]", "").strip().lower()
    sort_col_idx = request.args.get("order[0][column]", "0")
    sort_dir = request.args.get("order[0][dir]", "asc")

    # choose columns to display (common ones or first 6)
    display_cols = []
    candidates = [col_name, col_city, col_state, col_phone]
    for c in candidates:
        if c and c in df.columns:
            display_cols.append(c)
    if not display_cols:
        display_cols = list(df.columns[:6])

    # filtering
    if search:
        # simple contains search across the display columns
        mask = pd.Series(False, index=df.index)
        for c in display_cols:
            mask = mask | df[c].fillna("").astype(str).str.lower().str.contains(search)
        filtered = df[mask]
    else:
        filtered = df

    # sorting
    try:
        sort_col = display_cols[int(sort_col_idx)]
        filtered = filtered.sort_values(
            by=sort_col, 
            ascending=(sort_dir == "asc"),
            key=lambda col: col.astype(str).str.lower() if col.dtype == object else col,
            na_position="last"
        )
    except Exception as e:
        print("Sorting error:", e)
        # If sorting fails, proceed without sorting

    records_total = len(df)
    records_filtered = len(filtered)

    # pagination
    page = filtered.iloc[start:start + length]
    # convert to list of dicts with friendly keys
    data = []
    for _, r in page.iterrows():
        row = {}
        for c in display_cols:
            val = r.get(c, "")
            # convert numpy types
            if pd.isna(val):
                row[c] = ""
            else:
                row[c] = str(val)
        data.append(row)

    return jsonify({
        "recordsTotal": int(records_total),
        "recordsFiltered": int(records_filtered),
        "data": data
    })


@app.route("/api/predictions")
def api_predictions():
    """
    Light-weight prediction simulation.
    If date column exists: aggregate by month and fit linear trend.
    Else: compute counts per top-state and use numpy.polyfit to project + simple future estimate.
    Returns { history: [...], predictions: [...] }
    """
    history = []
    predictions = []

    if df is None or df.empty:
        return jsonify({"history": history, "predictions": predictions})

    # If a date-like column exists, attempt time-series on number of records per month
    if col_date and col_date in df.columns:
        try:
            # parse date column
            series = pd.to_datetime(df[col_date], errors="coerce")
            df_dates = pd.DataFrame({"d": series})
            df_dates["month"] = df_dates["d"].dt.to_period("M")
            counts = df_dates.groupby("month").size().reset_index(name="count")
            counts = counts.dropna()
            counts["x"] = np.arange(len(counts))
            x = counts["x"].values
            y = counts["count"].values
            if len(x) >= 2:
                p = np.polyfit(x, y, 1)
                # future 6 months
                future_x = np.arange(len(x), len(x) + 6)
                future_y = np.polyval(p, future_x)
                history = [{"period": str(m.month), "count": int(c)} for m, c in zip(counts["month"].astype(str), counts["count"])]
                predictions = [{"period": str(f), "predicted": float(max(0, round(yv, 2)))} for f, yv in zip(range(len(x), len(x)+6), future_y)]
                return jsonify({"history": history, "predictions": predictions})
        except Exception:
            pass

    # fallback: use counts per top states
    if col_state in df.columns:
        counts = df[col_state].fillna("Unknown").value_counts().head(10)
        history = [{"State": s, "count": int(c)} for s, c in counts.items()]
        # create simple linear model on ranks -> counts
        y = np.array([c for _, c in counts.items()], dtype=float)
        x = np.arange(len(y), dtype=float)
        if len(x) >= 2:
            coeffs = np.polyfit(x, y, 1)  # slope, intercept
            future_x = np.arange(len(y), len(y) + 5)
            future_y = np.polyval(coeffs, future_x)
            predictions = [{"future_index": int(ix), "predicted": float(max(0.0, round(val, 2)))} for ix, val in zip(future_x.tolist(), future_y.tolist())]
        else:
            predictions = [{"future_index": i, "predicted": float(int(y[0]) if len(y) else 0)} for i in range(len(y), len(y) + 5)]
        return jsonify({"history": history, "predictions": predictions})

    # final fallback: no data
    return jsonify({"history": history, "predictions": predictions})


@app.route("/api/data-quality")
def api_data_quality():
    """Return data quality metrics by column."""
    if df is None or df.empty:
        return jsonify({})
    
    quality_metrics = {}
    for col in df.columns:
        total = len(df)
        non_null = df[col].notna().sum()
        null_pct = (total - non_null) / total * 100 if total > 0 else 0
        unique = df[col].nunique()
        unique_pct = unique / total * 100 if total > 0 else 0
        
        # Sample values for preview
        sample_values = df[col].dropna().unique()[:5].tolist()
        
        quality_metrics[col] = {
            "total": total,
            "non_null": non_null,
            "null_pct": round(null_pct, 1),
            "unique": unique,
            "unique_pct": round(unique_pct, 1),
            "sample_values": sample_values
        }
    
    return jsonify(quality_metrics)


@app.route("/api/geographic-distribution")
def api_geographic_distribution():
    """Return geographic distribution data for mapping."""
    if df is None or df.empty or col_state not in df.columns:
        return jsonify({})
    
    state_counts = df[col_state].fillna("Unknown").value_counts().to_dict()
    
    # This would typically connect to a proper state mapping service
    # For now, return the counts and let the frontend handle mapping
    return jsonify(state_counts)


# Optional: download cached CSV
@app.route("/download/csv")
def download_csv():
    if os.path.exists(CACHE_CSV):
        return send_file(CACHE_CSV, as_attachment=True, download_name="principals_analytics_export.csv")
    # try to create on the fly
    try:
        temp = os.path.join(APP_DIR, "principals_export.csv")
        df.to_csv(temp, index=False)
        return send_file(temp, as_attachment=True, download_name="principals_analytics_export.csv")
    except Exception:
        return jsonify({"error": "No data available"}), 404


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # Set host=0.0.0.0 if you want external access on local network
    app.run(debug=True, port=5000)
