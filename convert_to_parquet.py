import pandas as pd

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
INPUT_FILE = "Primarydata.xlsx"
SHEET_NAME = "V2 Master Primary Data"
OUTPUT_PARQUET = "primary_sales.parquet"

# Month mapping (Apr–Dec)
MONTH_MAP = {
    "Apr": ("apr", 4,  "Apr"),
    "May": ("may", 5,  "May"),
    "Jun": ("jun", 6,  "Jun"),
    "Jul": ("jul", 7,  "Jul"),
    "Aug": ("aug", 8,  "Aug"),
    "Sep": ("sep", 9,  "Sep"),
    "Oct": ("oct", 10, "Oct"),
    "Nov": ("nov", 11, "Nov"),
    "Dec": ("dec", 12, "Dec"),
}
VALID_MONTHS = list(MONTH_MAP.keys())

# ------------------------------------------------------------
# LOAD RAW PRIMARY DATA
# ------------------------------------------------------------
df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

# Strip column names (very important)
df.columns = df.columns.str.strip()

# ------------------------------------------------------------
# RENAME COLUMNS (STANDARD SCHEMA)
# ------------------------------------------------------------
df = df.rename(columns={
    "Channels": "Channel",
    "Distribution Channels": "Distribution Channel",  # This becomes the streamlit filter column
    "Sub-Channel": "Sub-Channel",
    "Customer Name": "Customer Name",
    "Customer Group": "Customer Group",
    "State Name": "State Name",
    "Region Name": "Region Name",
    "Item Name": "Item Name",
    "Qty Sold": "Qty Sold",
    "Amount excluding tax": "Amount excluding tax",
    "L1 – Parent Category": "L1 Category",
    "L0 - Parent Category": "L0 Category"
})

# ------------------------------------------------------------
# BASIC CLEANING
# ------------------------------------------------------------
# Month cleanup
df["Month"] = df["Month"].astype(str).str.strip()

# Keep only Apr–Dec
df = df[df["Month"].isin(VALID_MONTHS)].copy()

# Drop "Out of State" rows (internal revenue)
if "Distribution Channel" in df.columns:
    df["Distribution Channel"] = df["Distribution Channel"].astype(str).str.strip()
    df = df[df["Distribution Channel"] != "Out of State"].copy()

# ------------------------------------------------------------
# MONTH KEYS
# ------------------------------------------------------------
df["MonthKey"]   = df["Month"].map(lambda x: MONTH_MAP[x][0])
df["MonthNum"]   = df["Month"].map(lambda x: MONTH_MAP[x][1])
df["MonthLabel"] = df["Month"].map(lambda x: MONTH_MAP[x][2])

# ------------------------------------------------------------
# TYPE FIXES (SAFE)
# ------------------------------------------------------------
# These help avoid bugs in Streamlit charts
if "Qty Sold" in df.columns:
    df["Qty Sold"] = pd.to_numeric(df["Qty Sold"], errors="coerce").fillna(0)

if "Amount excluding tax" in df.columns:
    df["Amount excluding tax"] = pd.to_numeric(df["Amount excluding tax"], errors="coerce").fillna(0)

# Optional: clean strings
for c in ["Channel", "Distribution Channel", "Sub-Channel", "Customer Group", "State Name", "Region Name", "Item Name", "L0 Category", "L1 Category"]:
    if c in df.columns:
        df[c] = df[c].astype(str).str.strip()

# ------------------------------------------------------------
# EXPORT TO PARQUET
# ------------------------------------------------------------
df.to_parquet(OUTPUT_PARQUET, index=False)

print("✅ Parquet export completed")
print("Rows:", len(df))
print("Months included:", sorted(df["Month"].unique(), key=lambda x: MONTH_MAP[x][1]))
