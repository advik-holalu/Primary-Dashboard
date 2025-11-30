import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="Primary Sales Dashboard", layout="wide")


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    return pd.read_parquet("primary_sales.parquet")

df = load_data().copy()


# ------------------------------------------------------------
# MONTH ORDER (FORCED)
# ------------------------------------------------------------
MONTH_ORDER = ["Apr","May","Jun","Jul","Aug","Sep","Oct"]
df["Month"] = pd.Categorical(df["Month"], MONTH_ORDER, ordered=True)

if "MonthNum" in df.columns:
    df = df.sort_values("MonthNum")
else:
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
tab1, tab2, = st.tabs(["Sales Overview", "Top Markets"])


# ============================================================
# TAB-1  SALES OVERVIEW  (UPDATED AS PER REQUEST)
# ============================================================
with tab1:

    st.title("Sales Overview")

    # KPI Blocks
    total_revenue  = filtered["Amount excluding tax"].sum()
    total_qty      = filtered["Qty Sold"].sum()
    unique_items   = filtered["Item Name"].nunique()
    active_states  = filtered["State Name"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", f"₹ {total_revenue:,.0f}")
    k2.metric("Total Qty Sold", f"{total_qty:,.0f}")
    k3.metric("Unique Products Sold", f"{unique_items}")
    k4.metric("Active States", f"{active_states}")


    # --------------------------------------------------------
    # MONTHLY CATEGORY TREND
    # --------------------------------------------------------
    monthly = (
        filtered.groupby(["Month","L0 Category"], observed=False)["Amount excluding tax"]
        .sum().reset_index()
    )
    monthly["Month"] = pd.Categorical(monthly["Month"], MONTH_ORDER, ordered=True)
    monthly = monthly.sort_values("Month")

    if monthly["Month"].nunique() <= 1:
        st.write("Insufficient month variation for trend analysis under current filters.")

    fig_monthly = px.line(
        monthly,
        x="Month", y="Amount excluding tax",
        color="L0 Category",
        markers=True,
        title="Monthly Revenue Trend by Category"
    )
    st.plotly_chart(fig_monthly, use_container_width=True)


    # --------------------------------------------------------
    # DISTRIBUTION CHANNEL GRAPH (NEW)
    # --------------------------------------------------------
    distr = (
        filtered.groupby("Distribution Channel", observed=False)["Amount excluding tax"]
        .sum().sort_values(ascending=False).reset_index()
    )

    fig_distr = px.bar(
        distr,
        x="Distribution Channel", y="Amount excluding tax",
        text_auto=True,
        color="Distribution Channel",
        title="Revenue by Distribution Channel"
    )
    fig_distr.update_layout(showlegend=False)
    st.plotly_chart(fig_distr, use_container_width=True)


    # --------------------------------------------------------
    # SUB-CHANNEL BREAKDOWN (RETAINED)
    # --------------------------------------------------------
    sub_rev = (
        filtered.groupby("Sub-Channel", observed=False)["Amount excluding tax"]
        .sum().sort_values(ascending=False).reset_index()
    )

    fig_sub = px.bar(
        sub_rev,
        x="Sub-Channel", y="Amount excluding tax",
        text_auto=True,
        color="Sub-Channel",
        title="Revenue by Sub-Channel"
    )
    fig_sub.update_layout(showlegend=False)
    st.plotly_chart(fig_sub, use_container_width=True)

    # --------------------------------------------------------
    # CUSTOMER GROUP BREAKDOWN (ADDED BACK)
    # --------------------------------------------------------
    cg_rev = (
        filtered.groupby("Customer Group", observed=False)["Amount excluding tax"]
        .sum().sort_values(ascending=False).reset_index()
    )

    fig_cg = px.bar(
        cg_rev,
        x="Customer Group", y="Amount excluding tax",
        text_auto=True,
        color="Customer Group",
        title="Revenue by Customer Group"
    )
    fig_cg.update_layout(showlegend=False)
    st.plotly_chart(fig_cg, use_container_width=True)

    # --------------------------------------------------------
    # Q1 / Q2 / OCT REGION COMPARISON (UNCHANGED)
    # --------------------------------------------------------
    def donut(df_slice, title):
        region_data = df_slice.groupby("Region Name", observed=False)["Amount excluding tax"].sum().reset_index()
        if region_data.empty:
            return None
        return px.pie(region_data, names="Region Name", values="Amount excluding tax", hole=0.45, title=title)

    q1   = filtered[filtered["Month"].isin(["Apr","May","Jun"])]
    q2   = filtered[filtered["Month"].isin(["Jul","Aug","Sep"])]
    octd = filtered[filtered["Month"] == "Oct"]

    c1, c2, c3 = st.columns(3)

    if fig1 := donut(q1, "Q1 Region Mix"):      c1.plotly_chart(fig1, use_container_width=True)
    if fig2 := donut(q2, "Q2 Region Mix"):      c2.plotly_chart(fig2, use_container_width=True)
    if fig3 := donut(octd, "October Region Mix"): c3.plotly_chart(fig3, use_container_width=True)


# ============================================================
# TAB-2  TOP 70 PERCENT MARKETS (STATE PERFORMANCE)
# ============================================================
with tab2:

    st.title("Top Markets")

    # ------------------------------------------------------------
    # Helper to determine Top 70% States (only from Q1 period)
    # ------------------------------------------------------------
    def top_70_states(df_period):
        if df_period.empty:
            return []
        grouped = (
            df_period.groupby("State Name", observed=False)["Amount excluding tax"]
            .sum().sort_values(ascending=False).reset_index()
        )
        grouped["Cumulative"] = grouped["Amount excluding tax"].cumsum() / grouped["Amount excluding tax"].sum() * 100
        top_states = grouped[grouped["Cumulative"] <= 70]["State Name"].tolist()
        return top_states or [grouped.iloc[0]["State Name"]]


    # Identify Q1 only (Apr-Jun)
    Q1  = filtered[filtered["Month"].isin(["Apr","May","Jun"])]
    Q2  = filtered[filtered["Month"].isin(["Jul","Aug","Sep"])]
    OCT = filtered[filtered["Month"] == "Oct"]

    q1_states = top_70_states(Q1)

    # Unified Color Map
    all_pool = list(set(q1_states))
    base_pal = px.colors.qualitative.Dark24 + px.colors.qualitative.Set3
    colormap = {s: base_pal[i % len(base_pal)] for i, s in enumerate(all_pool)}


    # ------------------------------------------------------------
    # Overall Apr–Oct Trend for only Q1 Top70 States
    # ------------------------------------------------------------
    st.subheader("Apr to Oct Trend (Filtered to Q1 Top 70% States)")

    if not Q1.empty:
        full_period = filtered[
            (filtered["Month"].isin(["Apr","May","Jun","Jul","Aug","Sep","Oct"])) &
            (filtered["State Name"].isin(q1_states))
        ]

        all_month = (
            full_period.groupby(["Month","State Name"], observed=False)["Amount excluding tax"]
            .sum().reset_index()
        )
        all_month["Month"] = pd.Categorical(all_month["Month"], MONTH_ORDER, ordered=True)
        all_month = all_month.sort_values("Month")

        fig_all = px.line(
            all_month,
            x="Month", y="Amount excluding tax",
            color="State Name",
            markers=True,
            color_discrete_map=colormap,
            title="Apr to Oct Trend (Only Q1 High Contribution States)"
        )
        st.plotly_chart(fig_all, use_container_width=True)
    else:
        st.write("No Q1 data exists under current filters, cannot compute top 70 states.")



    # ------------------------------------------------------------
    # Q1 Breakdown (Apr-Jun)
    # ------------------------------------------------------------
    st.subheader("Q1 State Performance")

    if Q1.empty:
        st.write("No Q1 data available for this filter.")
    else:
        q1_plot = (
            Q1[Q1["State Name"].isin(q1_states)]
            .groupby(["Month","State Name"], observed=False)["Amount excluding tax"]
            .sum().reset_index()
        )
        q1_plot["Month"] = pd.Categorical(q1_plot["Month"], ["Apr","May","Jun"], ordered=True)

        fig_q1 = px.line(
            q1_plot,
            x="Month", y="Amount excluding tax",
            color="State Name",
            markers=True,
            color_discrete_map=colormap,
            title="Q1 Monthly Revenue (Top Contribution States)"
        )
        st.plotly_chart(fig_q1, use_container_width=True)



    # ------------------------------------------------------------
    # Q2 Breakdown (Jul-Sep)
    # ------------------------------------------------------------
    st.subheader("Q2 State Performance")

    if Q2.empty:
        st.write("No Q2 data under current filters.")
    else:
        q2_plot = (
            Q2[Q2["State Name"].isin(q1_states)]
            .groupby(["Month","State Name"], observed=False)["Amount excluding tax"]
            .sum().reset_index()
        )
        q2_plot["Month"] = pd.Categorical(q2_plot["Month"], ["Jul","Aug","Sep"], ordered=True)

        fig_q2 = px.line(
            q2_plot,
            x="Month", y="Amount excluding tax",
            color="State Name",
            markers=True,
            color_discrete_map=colormap,
            title="Q2 Monthly Revenue (Filtered to Q1 Top States)"
        )
        st.plotly_chart(fig_q2, use_container_width=True)



    # ------------------------------------------------------------
    # October Snapshot
    # ------------------------------------------------------------
    st.subheader("October Snapshot")

    if OCT.empty:
        st.write("No October data found for this selection.")
    else:
        oct_plot = (
            OCT[OCT["State Name"].isin(q1_states)]
            .groupby("State Name", observed=False)["Amount excluding tax"]
            .sum().sort_values(ascending=False).reset_index()
        )

        fig_oct = px.bar(
            oct_plot,
            x="State Name", y="Amount excluding tax",
            text_auto=True,
            color="State Name",
            color_discrete_map=colormap,
            title="October Revenue Comparison (Only Q1 Top States)"
        )
        fig_oct.update_layout(showlegend=False)
        st.plotly_chart(fig_oct, use_container_width=True)
