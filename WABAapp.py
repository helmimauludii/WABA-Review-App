import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="NPX Messaging Dashboard", layout="wide")

st.title("📊 NPX Messaging Monitoring Dashboard")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("file waba streamlit.xlsx")
    df['Date'] = pd.to_datetime(df['Date'])
    df['template_category'] = df['template_category'].str.upper()
    df['status'] = df['status'].str.lower()
    return df

df = load_data()

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.header("🔎 Filter")

date_range = st.sidebar.date_input(
    "Date Range",
    [df['Date'].min(), df['Date'].max()]
)

account_list = sorted(df['account_no'].unique())
selected_accounts = st.sidebar.multiselect(
    "Account Number",
    account_list,
    default=account_list
)

df_filtered = df[
    (df['Date'] >= pd.to_datetime(date_range[0])) &
    (df['Date'] <= pd.to_datetime(date_range[1])) &
    (df['account_no'].isin(selected_accounts))
]

total_messages = df_filtered['count'].sum()

# =========================
# 1️⃣ TOTAL MESSAGE + STATUS
# =========================
st.subheader("1️⃣ Total Messages & Status Distribution")

status_summary = df_filtered.groupby('status')['count'].sum().reset_index()

col1, col2 = st.columns([1,2])

with col1:
    st.metric("📨 Total Messages Sent via NPX", f"{total_messages:,}")

with col2:
    fig_status = px.pie(
        status_summary,
        names='status',
        values='count',
        title="Message Status Distribution"
    )
    st.plotly_chart(fig_status, use_container_width=True)

# =========================
# 2️⃣ MESSAGE BY TYPE
# =========================
st.subheader("2️⃣ Messages by Type")

type_summary = df_filtered.groupby('template_category')['count'].sum().reset_index()

fig_type = px.bar(
    type_summary,
    x='template_category',
    y='count',
    text='count',
    title="Message Category Distribution"
)

st.plotly_chart(fig_type, use_container_width=True)

# =========================
# 3️⃣ ERROR VS TOTAL
# =========================
st.subheader("3️⃣ Error Code vs Total Messages")

error_df = df_filtered[df_filtered['error_msg'].notna()]

total_error = error_df['count'].sum()
success_messages = total_messages - total_error

error_compare = pd.DataFrame({
    "Type": ["Error Messages", "Non-Error Messages"],
    "Count": [total_error, success_messages]
})

fig_error_compare = px.bar(
    error_compare,
    x="Type",
    y="Count",
    text="Count",
    color="Type",
    title="Error vs Successful Messages"
)

st.plotly_chart(fig_error_compare, use_container_width=True)

st.subheader("4️⃣ Error Code Breakdown (Month on Month)")

error_df = df_filtered[df_filtered['error_msg'].notna()].copy()

if not error_df.empty:

    error_df['Month'] = error_df['Date'].dt.to_period('M').astype(str)

    # =========================
    # HITUNG TOTAL ERROR
    # =========================
    total_error_per_code = error_df.groupby('error_msg')['count'].sum().sort_values(ascending=False)

    TOP_N = 8
    top_errors = total_error_per_code.head(TOP_N).index

    # Label Others
    error_df['error_group'] = error_df['error_msg'].where(error_df['error_msg'].isin(top_errors), 'Others')

    # =========================
    # PIVOT
    # =========================
    error_pivot = error_df.pivot_table(
        index='Month',
        columns='error_group',
        values='count',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    error_long = error_pivot.melt(
        id_vars='Month',
        var_name='Error Code',
        value_name='Count'
    )

    error_long['Month'] = pd.to_datetime(error_long['Month'])
    error_long = error_long.sort_values('Month')
    error_long['Month'] = error_long['Month'].dt.strftime('%b %Y')

    # =========================
    # SOFT COLOR THEME
    # =========================
    soft_colors = [
        "#4C78A8", "#72B7B2", "#B279A2", "#F2CF5B",
        "#9D755D", "#BAB0AC", "#86BCB6", "#E0A458",
        "#8E6C8A"
    ]

    unique_errors = error_long["Error Code"].unique()
    color_map = {err: soft_colors[i % len(soft_colors)] for i, err in enumerate(unique_errors)}

    # =========================
    # CHART
    # =========================
    fig_error_stack = px.bar(
        error_long,
        x='Month',
        y='Count',
        color='Error Code',
        color_discrete_map=color_map,
        title=f"Monthly Error Code Breakdown (Top {TOP_N} Errors)",
        barmode='stack'
    )

    fig_error_stack.update_layout(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
            title="Error Code"
        ),
        margin=dict(t=60, b=120)
    )

    st.plotly_chart(fig_error_stack, use_container_width=True)

else:
    st.success("No error messages in selected filter 🎉")
