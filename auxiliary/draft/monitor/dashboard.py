import streamlit as st
import time
import pandas as pd
from monitor_core import SystemMonitor
import db

st.set_page_config(page_title="System Monitor", layout="wide", page_icon="🚀")

st.title("🚀 System Activity Monitor")

# Initialize monitor using cache_resource to persist across reruns/sessions appropriately
@st.cache_resource
def get_monitor():
    return SystemMonitor()

monitor = get_monitor()
db.init_db()

# Sidebar Navigation
page = st.sidebar.radio("Navigation", ["Live Dashboard", "Log History"], index=0)

if page == "Live Dashboard":
    st.title("🚀 Live Activity Monitor")

    # Create layout containers
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

    # Create placeholders for metrics to prevent appending
    cpu_metric = row1_col1.empty()
    gpu_metric = row1_col2.empty()
    ram_metric = row1_col3.empty()
    temp_metric = row1_col4.empty()

    disk_read_metric = row2_col1.empty()
    disk_write_metric = row2_col2.empty()
    net_up_metric = row2_col3.empty()
    net_down_metric = row2_col4.empty()

    st.markdown("### Activity History (Database 5s interval)")
    chart_placeholder = st.empty()

    # Run loop
    if 'running' not in st.session_state:
        st.session_state.running = True

    # Helper to format speed
    def fmt_speed(bytes_sec):
        if bytes_sec > 1024*1024: return f"{bytes_sec/1024/1024:.1f} MB/s"
        if bytes_sec > 1024: return f"{bytes_sec/1024:.1f} KB/s"
        return f"{bytes_sec:.0f} B/s"

    # Main loop
    while st.session_state.running:
        stats = monitor.get_stats()
        
        # 1. Metrics Row 1: Core Stats
        cpu_metric.metric("CPU Usage", f"{stats['cpu']:.1f}%")
        gpu_metric.metric("GPU Usage", f"{stats['gpu']}%")
        ram_metric.metric("RAM Usage", f"{stats['ram']:.1f}%")
        temp_metric.metric("Temperature", f"{stats['temp']}°C")
        
        # 2. Metrics Row 2: I/O Stats
        disk_read_metric.metric("Disk Read", fmt_speed(stats['disk']['read_speed']))
        disk_write_metric.metric("Disk Write", fmt_speed(stats['disk']['write_speed']))
        net_up_metric.metric("Net Up", fmt_speed(stats['net']['up_speed']))
        net_down_metric.metric("Net Down", fmt_speed(stats['net']['down_speed']))
        
        # 3. Chart from DB
        df = db.get_history(limit=60)
        if not df.empty:
            chart_data = df[['cpu', 'gpu', 'ram']].copy()
            chart_data.columns = ['CPU (%)', 'GPU (%)', 'RAM (%)']
            chart_placeholder.line_chart(chart_data)
        else:
            chart_placeholder.info("Waiting for data from logger. Run 'python logger.py' in background.")
        
        time.sleep(1)

elif page == "Log History":
    st.title("📜 Log History")
    
    st.markdown("View past activity logs stored in the database.")
    
    # Controls
    col1, col2 = st.columns([1, 3])
    with col1:
        limit = st.number_input("Rows to fetch", min_value=10, max_value=10000, value=200, step=50)
    
    # Fetch Data
    df = db.get_history(limit=limit)
    
    if not df.empty:
        # Sort newest first for table view (get_history returns chronological ASC)
        df_display = df.iloc[::-1].reset_index(drop=True)
        
        st.dataframe(df_display, use_container_width=True)
        
        # Download
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name='system_logs.csv',
            mime='text/csv',
        )
    else:
        st.warning("No data found in database. Make sure logger.py is running.")
