import pandas as pd

# ----------------------------------------
# Load raw primary data
# ----------------------------------------
df = pd.read_excel("Primarydata.xlsx", sheet_name="V2 Master Primary Data")

# ----------------------------------------
# Standardize & Rename Columns (NEW STRUCTURE)
# ----------------------------------------
df = df.rename(columns={
    "Day": "Day",
    "Month": "Month",
    "Year": "Year",
    "Channels": "Channel",                             # OLD: Channel - Retail/Online
    "Distribution Channels": "Distribution Channel",   # 🆕 NEW COLUMN ADDED
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

# ----------------------------------------
# Restrict to Apr–Oct (same logic retained)
# ----------------------------------------
valid_months = ["Apr","May","Jun","Jul","Aug","Sep","Oct"]
df = df[df["Month"].isin(valid_months)]

# ----------------------------------------
# Month Mapping Keys
# ----------------------------------------
month_map = {
    "Apr":("apr",4,"Apr"), "May":("may",5,"May"), "Jun":("jun",6,"Jun"),
    "Jul":("jul",7,"Jul"), "Aug":("aug",8,"Aug"), "Sep":("sep",9,"Sep"),
    "Oct":("oct",10,"Oct")
}

df["MonthKey"]   = df["Month"].apply(lambda x: month_map[x][0])
df["MonthNum"]   = df["Month"].apply(lambda x: month_map[x][1])
df["MonthLabel"] = df["Month"].apply(lambda x: month_map[x][2])

# ----------------------------------------
# Export to Parquet
# ----------------------------------------
df.to_parquet("primary_sales.parquet", index=False)
print("🟢 parquet regenerated successfully with NEW COLUMNS included")
