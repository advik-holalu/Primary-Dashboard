import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import math

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="Primary Sales Dashboard", layout="wide")


# ------------------------------------------------------------
# INR FORMATTERS
# ------------------------------------------------------------
def format_inr(n):
    """Metric formatter: shows ₹ in Lakhs/Crores."""
    try:
        n = float(n)
    except:
        return "₹ 0"

    abs_n = abs(n)

    if abs_n >= 1e7:
        return f"₹ {n/1e7:.2f} Cr"
    elif abs_n >= 1e5:
        return f"₹ {n/1e5:.2f} L"
    else:
        return f"₹ {n:,.0f}"


def inr_short(n):
    """Axis tick formatter: no ugly .00, supports 2Cr / 2.5Cr / 50L"""
    try:
        n = float(n)
    except:
        return "₹ 0"

    abs_n = abs(n)

    # Crores
    if abs_n >= 1e7:
        v = n / 1e7
        # show decimal only if needed
        if v.is_integer():
            return f"₹ {int(v)}Cr"
        else:
            return f"₹ {v:.1f}Cr"

    # Lakhs
    elif abs_n >= 1e5:
        v = n / 1e5
        if v.is_integer():
            return f"₹ {int(v)}L"
        else:
            return f"₹ {v:.1f}L"

    else:
        return f"₹ {n:,.0f}"

def apply_inr_ticks(fig, values):
    """
    Forces Plotly y-axis to show Lakhs/Crores instead of M.
    """
    if values is None or len(values) == 0:
        return fig

    vmax = float(pd.Series(values).max())
    if vmax <= 0:
        return fig

    # choose nice tick step
    if vmax >= 8e7:      # 8Cr+
        step = 2e7       # 2Cr step
    elif vmax >= 2e7:    # 2Cr+
        step = 5e6       # 50L step
    elif vmax >= 5e6:    # 50L+
        step = 1e6       # 10L step
    else:
        step = 5e5       # 5L step

    tickvals = list(np.arange(0, vmax + step, step))
    ticktext = [inr_short(v) for v in tickvals]

    fig.update_layout(
        yaxis=dict(
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext
        )
    )
    return fig


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    return pd.read_parquet("primary_sales.parquet")

df = load_data().copy()


# ------------------------------------------------------------
# CLEAN COLUMN NAMES (IMPORTANT)
# ------------------------------------------------------------
df.columns = df.columns.str.strip()


# ------------------------------------------------------------
# EXCLUDE INTERNAL REVENUE ("Out of State")
# ------------------------------------------------------------
out_state_col = None

if "Distribution Channels" in df.columns:
    out_state_col = "Distribution Channels"
elif "Distribution Channel" in df.columns:
    out_state_col = "Distribution Channel"

if out_state_col:
    df[out_state_col] = df[out_state_col].astype(str).str.strip()
    df = df[df[out_state_col] != "Out of State"].copy()
else:
    st.warning("Neither 'Distribution Channels' nor 'Distribution Channel' column found. Cannot exclude 'Out of State' rows.")


# ------------------------------------------------------------
# MONTH ORDER (AUTO - INCLUDES NOV/DEC)
# ------------------------------------------------------------
if "MonthNum" in df.columns:
    df["MonthNum"] = pd.to_numeric(df["MonthNum"], errors="coerce")

    month_order = (
        df.dropna(subset=["MonthNum", "Month"])
          .sort_values("MonthNum")["Month"]
          .astype(str)
          .str.strip()
          .drop_duplicates()
          .tolist()
    )

    df["Month"] = pd.Categorical(df["Month"].astype(str).str.strip(), categories=month_order, ordered=True)
    df = df.sort_values(["MonthNum", "Month"])

else:
    # fallback sort, only if MonthNum doesn't exist
    month_order = sorted(df["Month"].dropna().astype(str).str.strip().unique().tolist())
    df["Month"] = pd.Categorical(df["Month"].astype(str).str.strip(), categories=month_order, ordered=True)
    df = df.sort_values("Month")


# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("Filters")
filtered = df.copy()

channel_opts = ["All"] + sorted(df["Channel"].dropna().unique())
sel_channel = st.sidebar.multiselect("Channel", channel_opts, default=["All"])
if "All" not in sel_channel:
    filtered = filtered[filtered["Channel"].isin(sel_channel)]

dist_opts = ["All"] + sorted(filtered["Distribution Channel"].dropna().unique())
sel_dist = st.sidebar.multiselect("Distribution Channel", dist_opts, default=["All"])
if "All" not in sel_dist:
    filtered = filtered[filtered["Distribution Channel"].isin(sel_dist)]

sub_opts = ["All"] + sorted(filtered["Sub-Channel"].dropna().unique())
sel_sub = st.sidebar.multiselect("Sub-Channel", sub_opts, default=["All"])
if "All" not in sel_sub:
    filtered = filtered[filtered["Sub-Channel"].isin(sel_sub)]

cg_opts = ["All"] + sorted(filtered["Customer Group"].dropna().unique())
sel_cg = st.sidebar.multiselect("Customer Group", cg_opts, default=["All"])
if "All" not in sel_cg:
    filtered = filtered[filtered["Customer Group"].isin(sel_cg)]

region_opts = ["All"] + sorted(filtered["Region Name"].dropna().unique())
sel_region = st.sidebar.selectbox("Region", region_opts)
if sel_region != "All":
    filtered = filtered[filtered["Region Name"] == sel_region]

state_opts = ["All"] + sorted(filtered["State Name"].dropna().unique())
sel_state = st.sidebar.multiselect("State", state_opts, default=["All"])
if "All" not in sel_state:
    filtered = filtered[filtered["State Name"].isin(sel_state)]

cat_opts = ["All"] + sorted(filtered["L0 Category"].dropna().unique())
sel_cat = st.sidebar.multiselect("L0 Category", cat_opts, default=["All"])
if "All" not in sel_cat:
    filtered = filtered[filtered["L0 Category"].isin(sel_cat)]


# ------------------------------------------------------------
# TAB HEADERS
# ------------------------------------------------------------
tab1, tab2 = st.tabs(["Sales Overview", "Top Markets"])


# ============================================================
# TAB-1  SALES OVERVIEW
# ============================================================
with tab1:

    st.title("Sales Overview")

    # --------------------------------------------------------
    # KPI Blocks (INR)
    # --------------------------------------------------------
    total_revenue  = filtered["Amount excluding tax"].sum()
    total_qty      = filtered["Qty Sold"].sum()
    unique_items   = filtered["Item Name"].nunique()
    active_states  = filtered["State Name"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", format_inr(total_revenue))
    k2.metric("Total Qty Sold", f"{total_qty:,.0f}")
    k3.metric("Unique Products Sold", f"{unique_items}")
    k4.metric("Active States", f"{active_states}")


    # --------------------------------------------------------
    # MONTHLY CATEGORY TREND (AUTO MONTHS)
    # --------------------------------------------------------
    monthly = (
        filtered.groupby(["Month", "L0 Category"], observed=False)["Amount excluding tax"]
        .sum()
        .reset_index()
    )

    monthly["Month"] = pd.Categorical(
        monthly["Month"].astype(str).str.strip(),
        categories=month_order,
        ordered=True
    )
    monthly = monthly.sort_values("Month")

    if monthly["Month"].nunique() <= 1:
        st.write("Insufficient month variation for trend analysis under current filters.")
    else:
        fig_monthly = px.line(
            monthly,
            x="Month",
            y="Amount excluding tax",
            color="L0 Category",
            markers=True,
            title="Monthly Revenue Trend by Category"
        )

        fig_monthly.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (₹)"
        )

        fig_monthly = apply_inr_ticks(fig_monthly, monthly["Amount excluding tax"])
        st.plotly_chart(fig_monthly, use_container_width=True)


    # --------------------------------------------------------
    # REVENUE BY DISTRIBUTION CHANNEL
    # --------------------------------------------------------
    distr = (
        filtered.groupby("Distribution Channel", observed=False)["Amount excluding tax"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    if distr.empty:
        st.write("No Distribution Channel data under current filters.")
    else:
        fig_distr = px.bar(
            distr,
            x="Distribution Channel",
            y="Amount excluding tax",
            text_auto=True,
            color="Distribution Channel",
            title="Revenue by Distribution Channel"
        )

        fig_distr.update_layout(
            showlegend=False,
            xaxis_title="Distribution Channel",
            yaxis_title="Revenue (₹)"
        )

        fig_distr = apply_inr_ticks(fig_distr, distr["Amount excluding tax"])
        st.plotly_chart(fig_distr, use_container_width=True)


    # --------------------------------------------------------
    # SUB-CHANNEL BREAKDOWN
    # --------------------------------------------------------
    sub_rev = (
        filtered.groupby("Sub-Channel", observed=False)["Amount excluding tax"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    if sub_rev.empty:
        st.write("No Sub-Channel data under current filters.")
    else:
        fig_sub = px.bar(
            sub_rev,
            x="Sub-Channel",
            y="Amount excluding tax",
            text_auto=True,
            color="Sub-Channel",
            title="Revenue by Sub-Channel"
        )

        fig_sub.update_layout(
            showlegend=False,
            xaxis_title="Sub-Channel",
            yaxis_title="Revenue (₹)"
        )

        fig_sub = apply_inr_ticks(fig_sub, sub_rev["Amount excluding tax"])
        st.plotly_chart(fig_sub, use_container_width=True)


    # --------------------------------------------------------
    # CUSTOMER GROUP BREAKDOWN
    # --------------------------------------------------------
    cg_rev = (
        filtered.groupby("Customer Group", observed=False)["Amount excluding tax"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    if cg_rev.empty:
        st.write("No Customer Group data under current filters.")
    else:
        fig_cg = px.bar(
            cg_rev,
            x="Customer Group",
            y="Amount excluding tax",
            text_auto=True,
            color="Customer Group",
            title="Revenue by Customer Group"
        )

        fig_cg.update_layout(
            showlegend=False,
            xaxis_title="Customer Group",
            yaxis_title="Revenue (₹)"
        )

        fig_cg = apply_inr_ticks(fig_cg, cg_rev["Amount excluding tax"])
        st.plotly_chart(fig_cg, use_container_width=True)


    # --------------------------------------------------------
    # Q1 / Q2 / Q3 REGION MIX (Q3 = Oct+Nov+Dec)
    # --------------------------------------------------------
    st.subheader("Quarterly Region Mix")

    def donut(df_slice, title):
        region_data = (
            df_slice.groupby("Region Name", observed=False)["Amount excluding tax"]
            .sum()
            .reset_index()
        )
        if region_data.empty:
            return None

        fig = px.pie(
            region_data,
            names="Region Name",
            values="Amount excluding tax",
            hole=0.45,
            title=title
        )

        # Show INR in hover
        fig.update_traces(
            hovertemplate="%{label}<br>Revenue=%{value:,.0f}<extra></extra>"
        )
        return fig

    # Dynamic quarter month buckets
    q1_months = month_order[:3]
    q2_months = month_order[3:6]
    q3_months = month_order[6:9]  # should become Oct-Nov-Dec when present

    Q1 = filtered[filtered["Month"].isin(q1_months)]
    Q2 = filtered[filtered["Month"].isin(q2_months)]
    Q3 = filtered[filtered["Month"].isin(q3_months)]

    c1, c2, c3 = st.columns(3)

    if fig1 := donut(Q1, f"Q1 Region Mix ({', '.join(q1_months)})"):
        c1.plotly_chart(fig1, use_container_width=True)
    else:
        c1.info("No Q1 data under current filters.")

    if fig2 := donut(Q2, f"Q2 Region Mix ({', '.join(q2_months)})"):
        c2.plotly_chart(fig2, use_container_width=True)
    else:
        c2.info("No Q2 data under current filters.")

    if q3_months:
        if fig3 := donut(Q3, f"Q3 Region Mix ({', '.join(q3_months)})"):
            c3.plotly_chart(fig3, use_container_width=True)
        else:
            c3.info("No Q3 data under current filters.")
    else:
        c3.info("Q3 months not present in dataset yet.")

# ============================================================
# TAB-2  TOP MARKETS (STATE PERFORMANCE)
# ============================================================
with tab2:

    st.title("Top Markets")

    # ------------------------------------------------------------
    # Helper: Top 70% states function
    # ------------------------------------------------------------
    def top_70_states(df_period):
        if df_period.empty:
            return []

        grouped = (
            df_period.groupby("State Name", observed=False)["Amount excluding tax"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        total = grouped["Amount excluding tax"].sum()
        if total <= 0:
            return []

        grouped["Cumulative"] = grouped["Amount excluding tax"].cumsum() / total * 100
        top_states = grouped[grouped["Cumulative"] <= 70]["State Name"].tolist()

        # if nothing falls <=70, at least keep top state
        return top_states or [grouped.iloc[0]["State Name"]]


    # ------------------------------------------------------------
    # Define Q1/Q2/Q3 months dynamically from month_order
    # ------------------------------------------------------------
    q1_months = month_order[:3]     # Apr-May-Jun
    q2_months = month_order[3:6]    # Jul-Aug-Sep
    q3_months = month_order[6:9]    # Oct-Nov-Dec (if present)

    Q1 = filtered[filtered["Month"].isin(q1_months)]
    Q2 = filtered[filtered["Month"].isin(q2_months)]
    Q3 = filtered[filtered["Month"].isin(q3_months)]


    # ------------------------------------------------------------
    # Compute Top 70% States based on Q1
    # ------------------------------------------------------------
    q1_states = top_70_states(Q1)

    if not q1_states:
        st.warning("No valid Q1 data under current filters, cannot compute Top 70% states.")
        st.stop()


    # ------------------------------------------------------------
    # Color map for consistency across charts
    # ------------------------------------------------------------
    all_pool = list(set(q1_states))
    base_pal = px.colors.qualitative.Dark24 + px.colors.qualitative.Set3
    colormap = {s: base_pal[i % len(base_pal)] for i, s in enumerate(all_pool)}


    # ------------------------------------------------------------
    # FULL PERIOD TREND (Apr–Dec) for Q1 Top States
    # ------------------------------------------------------------
    st.subheader(f"Full Period Trend ({month_order[0]} to {month_order[-1]}) — Only Q1 Top 70% States")

    full_period = filtered[
        (filtered["Month"].isin(month_order)) &
        (filtered["State Name"].isin(q1_states))
    ].copy()

    if full_period.empty:
        st.write("No data after applying top state filters.")
    else:
        full_month = (
            full_period.groupby(["Month", "State Name"], observed=False)["Amount excluding tax"]
            .sum()
            .reset_index()
        )

        full_month["Month"] = pd.Categorical(
            full_month["Month"].astype(str).str.strip(),
            categories=month_order,
            ordered=True
        )
        full_month = full_month.sort_values("Month")

        fig_all = px.line(
            full_month,
            x="Month",
            y="Amount excluding tax",
            color="State Name",
            markers=True,
            color_discrete_map=colormap,
            title="Monthly Revenue Trend (Top Contribution States)"
        )

        fig_all.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (₹)"
        )

        fig_all = apply_inr_ticks(fig_all, full_month["Amount excluding tax"])
        st.plotly_chart(fig_all, use_container_width=True)


    # ------------------------------------------------------------
    # Q1 Breakdown
    # ------------------------------------------------------------
    st.subheader(f"Q1 State Performance ({', '.join(q1_months)})")

    q1_plot = (
        Q1[Q1["State Name"].isin(q1_states)]
        .groupby(["Month", "State Name"], observed=False)["Amount excluding tax"]
        .sum()
        .reset_index()
    )

    if q1_plot.empty:
        st.write("No Q1 data available for this filter.")
    else:
        q1_plot["Month"] = pd.Categorical(
            q1_plot["Month"].astype(str).str.strip(),
            categories=q1_months,
            ordered=True
        )

        fig_q1 = px.line(
            q1_plot,
            x="Month",
            y="Amount excluding tax",
            color="State Name",
            markers=True,
            color_discrete_map=colormap,
            title="Q1 Monthly Revenue (Top Contribution States)"
        )

        fig_q1.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (₹)"
        )

        fig_q1 = apply_inr_ticks(fig_q1, q1_plot["Amount excluding tax"])
        st.plotly_chart(fig_q1, use_container_width=True)


    # ------------------------------------------------------------
    # Q2 Breakdown
    # ------------------------------------------------------------
    st.subheader(f"Q2 State Performance ({', '.join(q2_months)})")

    q2_plot = (
        Q2[Q2["State Name"].isin(q1_states)]
        .groupby(["Month", "State Name"], observed=False)["Amount excluding tax"]
        .sum()
        .reset_index()
    )

    if q2_plot.empty:
        st.write("No Q2 data under current filters.")
    else:
        q2_plot["Month"] = pd.Categorical(
            q2_plot["Month"].astype(str).str.strip(),
            categories=q2_months,
            ordered=True
        )

        fig_q2 = px.line(
            q2_plot,
            x="Month",
            y="Amount excluding tax",
            color="State Name",
            markers=True,
            color_discrete_map=colormap,
            title="Q2 Monthly Revenue (Filtered to Q1 Top States)"
        )

        fig_q2.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (₹)"
        )

        fig_q2 = apply_inr_ticks(fig_q2, q2_plot["Amount excluding tax"])
        st.plotly_chart(fig_q2, use_container_width=True)


    # ------------------------------------------------------------
    # Q3 Breakdown (Oct-Nov-Dec)
    # ------------------------------------------------------------
    st.subheader(f"Q3 State Performance ({', '.join(q3_months)})")

    if not q3_months:
        st.info("Q3 months not present in dataset yet.")
    else:
        q3_plot = (
            Q3[Q3["State Name"].isin(q1_states)]
            .groupby(["Month", "State Name"], observed=False)["Amount excluding tax"]
            .sum()
            .reset_index()
        )

        if q3_plot.empty:
            st.write("No Q3 data under current filters.")
        else:
            q3_plot["Month"] = pd.Categorical(
                q3_plot["Month"].astype(str).str.strip(),
                categories=q3_months,
                ordered=True
            )

            fig_q3 = px.line(
                q3_plot,
                x="Month",
                y="Amount excluding tax",
                color="State Name",
                markers=True,
                color_discrete_map=colormap,
                title="Q3 Monthly Revenue (Filtered to Q1 Top States)"
            )

            fig_q3.update_layout(
                xaxis_title="Month",
                yaxis_title="Revenue (₹)"
            )

            fig_q3 = apply_inr_ticks(fig_q3, q3_plot["Amount excluding tax"])
            st.plotly_chart(fig_q3, use_container_width=True)


    # ------------------------------------------------------------
    # Latest Month Snapshot (instead of hardcoded Oct)
    # ------------------------------------------------------------
    latest_month = month_order[-1]
    st.subheader(f"{latest_month} Snapshot")

    latest_df = filtered[
        (filtered["Month"].astype(str) == latest_month) &
        (filtered["State Name"].isin(q1_states))
    ]

    if latest_df.empty:
        st.write(f"No data found for {latest_month} under current filter selection.")
    else:
        latest_plot = (
            latest_df.groupby("State Name", observed=False)["Amount excluding tax"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        fig_latest = px.bar(
            latest_plot,
            x="State Name",
            y="Amount excluding tax",
            text_auto=True,
            color="State Name",
            color_discrete_map=colormap,
            title=f"{latest_month} Revenue Comparison (Only Q1 Top States)"
        )

        fig_latest.update_layout(
            showlegend=False,
            xaxis_title="State",
            yaxis_title="Revenue (₹)"
        )

        fig_latest = apply_inr_ticks(fig_latest, latest_plot["Amount excluding tax"])
        st.plotly_chart(fig_latest, use_container_width=True)
