import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np

# --- 1. Basic Setup, Data Loading, and Helper Functions ---

# Set the page configuration for a wider layout
st.set_page_config(layout="wide", page_title="Current Air Quality Map")

# Helper function to map AQI score to a descriptive health category and color
def aqi_category(aqi):
    """Maps AQI score to a descriptive health category and color (based on US EPA standard)."""
    # Ensure AQI is an integer for accurate comparison
    aqi = int(aqi)
    if aqi <= 50:
        return 'Good', '#009966'
    elif aqi <= 100:
        return 'Moderate', '#ffde33'
    elif aqi <= 150:
        return 'Unhealthy for Sensitive Groups', '#ff9933'
    elif aqi <= 200:
        return 'Unhealthy', '#cc0033'
    elif aqi <= 300:
        return 'Very Unhealthy', '#660099'
    else: # > 300
        return 'Hazardous', '#7e0023'

# Use st.cache_data to load the CSV only once for performance
@st.cache_data
def load_data():
    """Loads, cleans, and prepares ALL air quality data records (Current and Past)."""
    file_path = 'AQI_Thailand_FINAL_DATA_20251207_142243.csv'
    try:
        df = pd.read_csv(file_path)
        
        # Convert date/time columns to proper datetime objects.
        # errors='coerce' turns invalid parsing (like 'N/A') into NaT (Not a Time/Date)
        # .dt.date is used for record_date to strip the time part for clean date filtering
        df['record_date'] = pd.to_datetime(df['record_date'], errors='coerce').dt.date
        df['time_utc'] = pd.to_datetime(df['time_utc'], errors='coerce')
        
        # Clean 'aqi_overall' by replacing 'N/A' (from Past data rows) with 0 before converting to integer
        df['aqi_overall'] = df['aqi_overall'].replace('N/A', 0).astype(int)
        
        # Apply the helper function to create new columns for coloring/display
        df[['aqi_category', 'color_code']] = df['aqi_overall'].apply(
            lambda x: pd.Series(aqi_category(x))
        )
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure it is in the same directory.")
        st.stop()
    
df = load_data()

# --- 2. Title and Sidebar ---

st.title("🗺️ Current Air Quality Index (AQI) Across Stations")
st.markdown("Visualize the real-time AQI and specific pollutant levels across monitoring stations.")
st.sidebar.header("Filter & View Options")

# --- 3. Sidebar Filtering (Interactivity) ---

# --- Record Type Toggle ---
st.sidebar.subheader("Record Type")

# Initialize df_filtered with the full dataset copy
df_filtered = df.copy()

# Checkbox for "Current" data only
show_current_only = st.sidebar.checkbox("Current (12-7-2025) (Not including forecasts)", value=False, help="Show only current data from 2025-12-07")

# Apply Current filter if checkbox is checked
if show_current_only:
    df_filtered = df_filtered[df_filtered['record_type'] == 'Current']

st.sidebar.markdown("---")
st.sidebar.subheader("Date Range")

# Calculate overall min/max dates for picker limits
max_date_overall = df['record_date'].max()
min_date_overall = df['record_date'].min()

# Calculate min/max dates from the currently filtered data (for initial value)
min_date_filtered = df_filtered['record_date'].min()
max_date_filtered = df_filtered['record_date'].max()


# Handle edge case where filtered data is empty
if pd.isna(min_date_filtered):
    st.sidebar.warning("No data available for the selected record type.")
    min_date_filtered = pd.to_datetime('today').date()
    max_date_filtered = pd.to_datetime('today').date()
    
# Store initial filtered dates for comparison
if 'initial_min_date' not in st.session_state:
    st.session_state['initial_min_date'] = min_date_filtered
if 'initial_max_date' not in st.session_state:
    st.session_state['initial_max_date'] = max_date_filtered


# 1. From Date
from_date = st.sidebar.date_input(
    'From Date:',
    value=min_date_filtered,
    min_value=min_date_overall,
    max_value=max_date_overall,
    disabled=df_filtered.empty or show_current_only,
    key='from_date_input'
)

# 2. To Date
to_date = st.sidebar.date_input(
    'To Date:',
    value=max_date_filtered,
    min_value=min_date_overall,
    max_value=max_date_overall,
    disabled=df_filtered.empty or show_current_only,
    key='to_date_input'
)

date_range_changed = (
    (from_date != st.session_state['initial_min_date']) or 
    (to_date != st.session_state['initial_max_date'])
)

# Apply the Date Filter Logic
if not df_filtered.empty:
    # If "Current" is checked, use only 2025-12-07
    if show_current_only:
        current_date = pd.to_datetime('2025-12-07').date()
        df_filtered = df_filtered[df_filtered['record_date'] == current_date]
    else:
        # Ensure 'From Date' is not after 'To Date'
        if from_date > to_date:
            st.sidebar.error("Error: 'From Date' cannot be after 'To Date'.")
            # Swap them to maintain filtering logic
            start_date = to_date
            end_date = from_date
        else:
            start_date = from_date
            end_date = to_date
            
        # Apply the date range filter
        df_filtered = df_filtered[
            (df_filtered['record_date'] >= start_date) & 
            (df_filtered['record_date'] <= end_date)
        ]

st.sidebar.markdown("---")
st.sidebar.subheader("Location & Pollutant Filters")

# Selector for City/Station (This uses df_filtered now)
city_names = ['All Stations'] + df_filtered['city_name'].unique().tolist()
selected_city = st.sidebar.selectbox(
    'Select Station Location',
    city_names
)

# Apply City Filter
if selected_city != 'All Stations':
    df_filtered = df_filtered[df_filtered['city_name'] == selected_city]

# Slider for Pollutant Threshold
# Note: min/max values are taken from the overall df to avoid filter cascade issues
pm25_min_overall = float(df['pm25'].min())
pm25_max_overall = float(df['pm25'].max())

# --- MODIFIED: Combined PM2.5 Range Slider ---
pm25_range = st.sidebar.slider(
    'PM2.5 Level Range (µg/m³)',
    min_value=0.0,
    max_value=pm25_max_overall,
    # Default to the entire range (0 to max)
    value=(0.0, pm25_max_overall), 
    step=1.0
)

# Extract min and max from the tuple
pm25_min_threshold = pm25_range[0]
pm25_max_threshold = pm25_range[1]

# Apply PM2.5 filters
df_filtered = df_filtered[
    (df_filtered['pm25'] >= pm25_min_threshold) &
    (df_filtered['pm25'] <= pm25_max_threshold)
].reset_index(drop=True)

# --- 4. Key Summary Metrics ---

st.subheader("Key Air Quality Summary")

if not df_filtered.empty:
    # Calculate the maximum AQI and its corresponding station
    max_aqi = df_filtered['aqi_overall'].max()
    # Handle cases where multiple stations have the max AQI, just take the first one
    worst_station = df_filtered[df_filtered['aqi_overall'] == max_aqi]['city_name'].iloc[0]

    # Display metrics in columns
    col1, col2, col3 = st.columns(3)

    col1.metric(
        label="Maximum AQI",
        value=f"{max_aqi}",
        delta=f"at {worst_station}",
        delta_color="off" # Use off as delta field is descriptive, not a change
    )
    col2.metric(
        label="Average PM2.5 (µg/m³)",
        value=f"{df_filtered['pm25'].mean():.1f}"
    )
    col3.metric(
        label="Records Shown",
        value=len(df_filtered)
    )
    st.markdown("---")
    
# --- 5. Geospatial Map Visualization (Plotly Express) ---

st.header("Air Quality Map (Color by Health Category)")

# Check if there's data to plot after filtering
if not df_filtered.empty:
    
    # Define the order and discrete color map for Plotly
    category_order = ['Good', 'Moderate', 'Unhealthy for Sensitive Groups', 'Unhealthy', 'Very Unhealthy', 'Hazardous']
    # Create the color map dictionary for Plotly
    color_map = {cat: aqi_category(i * 51)[1] for i, cat in enumerate(category_order)} 
    
    # Create the scatter_mapbox figure using Plotly Express
    fig = px.scatter_mapbox(
        df_filtered,
        lat="latitude",
        lon="longitude",
        color="aqi_category",              # Color the points by the category string
        size="pm25",                       # Size the points by PM2.5 concentration
        hover_name="city_name",
        hover_data={
            "pm25": ':.1f',
            "aqi_overall": True,
            "aqi_category": True,          # Include category in tooltip
            "latitude": False,
            "longitude": False,
            "temp": ':.1f',
        },
        category_orders={"aqi_category": category_order}, # Ensures the legend is in the correct order
        color_discrete_map=color_map,      # Use the discrete color mapping
        zoom=5, 
        height=600,
    )
    
    # Update map style and layout
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    
    # Display the Plotly chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)
    

else:
    st.warning("No stations match the selected filter criteria. Try changing the record type toggle or reducing the minimum PM2.5 threshold.")

# --- 6. Data Table Preview (Enhanced with st.data_editor) ---

st.markdown("---")
st.header("Filtered Data Table")
st.caption(f"Showing {len(df_filtered)} of {len(df)} total records (before record type filter).")

if not df_filtered.empty:
    # Use st.data_editor for interactive table experience
    st.data_editor(
        # CRITICAL CHANGE: Added 'record_date' and included 'record_type' for clarity
        df_filtered[['record_type', 'city_name', 'record_date', 'time_utc', 'aqi_overall', 'aqi_category', 'pm25', 'pm10', 'o3', 'temp', 'humidity']],
        
        # Using NumberColumn for AQI and PM2.5 to avoid the Progress compatibility error
        column_config={
            "aqi_overall": st.column_config.NumberColumn(
                "Overall AQI",
                format="%d",
            ),
            "pm25": st.column_config.NumberColumn("PM2.5", format="%.1f µg/m³"),
            "city_name": "Station Location",
            "aqi_category": "Health Category"
        },
        hide_index=True,
        use_container_width=True
    )