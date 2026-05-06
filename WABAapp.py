import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="NPX Messaging Dashboard", layout="wide")

st.title("📊 NPX Messaging Monitoring Dashboard")

# =========================
# FILE UPLOADER
# =========================
st.sidebar.header("📂 Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your data file", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("👋 Silakan upload file data (CSV atau Excel) di sidebar sebelah kiri untuk menampilkan dashboard.")
    st.stop() # Menghentikan eksekusi script sampai file diupload

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data(file):
    # Cek ekstensi file untuk menentukan fungsi pandas yang tepat
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
        
    # Validasi keberadaan kolom sesuai dengan format terbaru
    required_columns = ['date', 'account_no', 'template_category', 'template_name', 'status', 'total_messages']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        st.error(f"❌ File tidak valid. Kolom berikut tidak ditemukan: {', '.join(missing_cols)}")
        st.stop()
        
    # Jika kolom error_message tidak ada, buat kolom kosong agar script di bawah tidak error
    if 'error_message' not in df.columns:
        df['error_message'] = pd.NA
        
    # Cleaning data & Handle Null (kosong)
    df['date'] = pd.to_datetime(df['date'])
    
    # Isi nilai kosong pada kategori dan template agar grafik tidak error
    df['template_category'] = df['template_category'].fillna('UNKNOWN').astype(str).str.upper()
    df['template_name'] = df['template_name'].fillna('NO TEMPLATE').astype(str)
    
    df['status'] = df['status'].astype(str).str.lower()
    
    return df

# Load data dari file yang diupload
df = load_data(uploaded_file)

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.header("🔎 Filter")

# 🎯 Default range otomatis menyesuaikan data yang diupload
default_start = df['date'].min().date()
default_end = df['date'].max().date()

date_range = st.sidebar.date_input(
    "Date Range",
    value=[default_start, default_end],
    min_value=default_start,
    max_value=default_end
)

# Validasi input tanggal
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    st.warning("📅 Please select both start and end dates.")
    st.stop()

account_list = sorted(df['account_no'].dropna().unique())
selected_accounts = st.sidebar.multiselect(
    "Account Number",
    account_list,
    default=account_list
)

# Filter Dataset
df_filtered = df[
    (df['date'] >= pd.to_datetime(start_date)) &
    (df['date'] <= pd.to_datetime(end_date)) &
    (df['account_no'].isin(selected_accounts))
]

total_messages = df_filtered['total_messages'].sum()

# =========================
# 1️⃣ TOTAL MESSAGE + STATUS
# =========================
st.subheader("1️⃣ Total Messages & Status Distribution")

status_summary = df_filtered.groupby('status')['total_messages'].sum().reset_index()

col1, col2 = st.columns([1,2])

with col1:
    st.metric("📨 Total Messages Sent via NPX", f"{total_messages:,}")

with col2:
    fig_status = px.pie(
        status_summary,
        names='status',
        values='total_messages',
        title="Message Status Distribution"
    )
    st.plotly_chart(fig_status, use_container_width=True)

# =========================
# 2️⃣ MESSAGE BY TYPE
# =========================
st.subheader("2️⃣ Messages by Type")

type_summary = df_filtered.groupby('template_category')['total_messages'].sum().reset_index()

fig_type = px.bar(
    type_summary,
    x='template_category',
    y='total_messages',
    text='total_messages',
    title="Message Category Distribution"
)

st.plotly_chart(fig_type, use_container_width=True)

# =========================
# 3️⃣ ERROR VS TOTAL
# =========================
st.subheader("3️⃣ Error vs Total Messages")

# Ambil data error (pastikan tidak null dan bukan string kosong)
error_df = df_filtered[df_filtered['error_message'].notna() & (df_filtered['error_message'].astype(str).str.strip() != "")]

total_error = error_df['total_messages'].sum()
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

# =========================
# 4️⃣ ERROR CODE BREAKDOWN
# =========================
st.subheader("4️⃣ Error Code Breakdown (Month on Month)")

if not error_df.empty and total_error > 0:

    error_df['Month'] = error_df['date'].dt.to_period('M').astype(str)

    # HITUNG TOTAL ERROR PER KODE
    total_error_per_code = error_df.groupby('error_message')['total_messages'].sum().sort_values(ascending=False)

    TOP_N = 8
    top_errors = total_error_per_code.head(TOP_N).index

    # Label Others
    error_df['error_group'] = error_df['error_message'].where(error_df['error_message'].isin(top_errors), 'Others')

    # PIVOT
    error_pivot = error_df.pivot_table(
        index='Month',
        columns='error_group',
        values='total_messages',
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

    # SOFT COLOR THEME
    soft_colors = [
        "#4C78A8", "#72B7B2", "#B279A2", "#F2CF5B",
        "#9D755D", "#BAB0AC", "#86BCB6", "#E0A458",
        "#8E6C8A"
    ]

    unique_errors = error_long["Error Code"].unique()
    color_map_err = {err: soft_colors[i % len(soft_colors)] for i, err in enumerate(unique_errors)}

    # CHART
    fig_error_stack = px.bar(
        error_long,
        x='Month',
        y='Count',
        color='Error Code',
        color_discrete_map=color_map_err,
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

# =========================
# 5️⃣ TEMPLATE STATUS DISTRIBUTION
# =========================
st.subheader("5️⃣ Template Name Distribution")

# Filter agar template yang kosong ("NO TEMPLATE") tidak mendominasi chart jika tidak diinginkan
# (opsional, saat ini dimasukkan semua)
template_status = df_filtered.groupby(['template_name', 'status'])['total_messages'].sum().reset_index()

template_pivot = template_status.pivot(index='template_name', columns='status', values='total_messages').fillna(0)

# Pastikan kolom status standar ada meskipun tidak ada di data agar tidak error
for s in ['delivered', 'failed', 'read', 'sent']:
    if s not in template_pivot.columns:
        template_pivot[s] = 0

# Hitung total per template
template_pivot['total'] = template_pivot.sum(axis=1)
template_pivot = template_pivot.sort_values(by='total', ascending=False)

total_templates = template_pivot.shape[0]

if total_templates > 0:
    # 🎛 Kontrol Top N
    colA, colB = st.columns([1,3])

    with colA:
        top_n = st.number_input(
            "Show Top N Templates",
            min_value=1,
            max_value=total_templates,
            value=min(20, total_templates),
            step=5
        )

    with colB:
        st.markdown(f"**Total Template Names Available:** {total_templates}")

    # Ambil sesuai Top N
    template_view = template_pivot.head(top_n).reset_index()
    title_text = f"Top {top_n} Templates — Status Distribution"

    # Ambil kolom status yang ada secara dinamis untuk melt
    status_columns = [col for col in template_pivot.columns if col != 'total']

    # Ubah ke long format
    template_long = template_view.melt(
        id_vars='template_name',
        value_vars=status_columns,
        var_name='Status',
        value_name='Count'
    )

    # Warna konsisten
    color_map = {
        'delivered': '#4C78A8',
        'failed': '#E45756',
        'read': '#72B7B2',
        'sent': '#F2CF5B'
    }

    # Chart
    fig_template_status = px.bar(
        template_long,
        x='Count',
        y='template_name',
        color='Status',
        orientation='h',
        title=title_text,
        color_discrete_map=color_map,
        barmode='stack'
    )

    fig_template_status.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig_template_status, use_container_width=True)
else:
    st.info("No template data available for this selection.")
