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
    """Loads and returns the clean air quality data with added category columns."""
    file_path = 'AQI_Thailand_FINAL_DATA_20251207_142243.csv'
    try:
        df = pd.read_csv(file_path)
        
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

# Selector for City/Station
city_names = ['All Stations'] + df['city_name'].unique().tolist()
selected_city = st.sidebar.selectbox(
    'Select Station Location',
    city_names
)

# Filter the DataFrame based on the user selection
if selected_city != 'All Stations':
    df_filtered = df[df['city_name'] == selected_city]
else:
    df_filtered = df.copy()

# Slider for Pollutant Threshold
pm25_min = float(df['pm25'].min())
pm25_max = float(df['pm25'].max())
pm25_threshold = st.sidebar.slider(
    'Minimum PM2.5 Level (µg/m³)',
    min_value=0.0, # Start from 0 for better UX
    max_value=pm25_max,
    value=0.0, # Default: show all
    step=1.0
)

# Apply PM2.5 filter
df_filtered = df_filtered[df_filtered['pm25'] >= pm25_threshold].reset_index(drop=True)

# --- 4. Key Summary Metrics (New Section) ---

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
        label="Stations Shown",
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
    # We use the aqi_category function logic to generate the map: 'Good' -> '#009966', etc.
    color_map = {cat: aqi_category(i * 51)[1] for i, cat in enumerate(category_order)} # Using proxy AQI values to get the color code
    
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
    st.warning("No stations match the selected filter criteria. Try reducing the minimum PM2.5 threshold.")

# --- 6. Data Table Preview (Enhanced with st.data_editor) ---

st.markdown("---")
st.header("Filtered Data Table")
st.caption(f"Showing {len(df_filtered)} of {len(df)} total records.")

# Use st.data_editor for interactive table experience
st.data_editor(
    df_filtered[['city_name', 'time_utc', 'aqi_overall', 'aqi_category', 'pm25', 'pm10', 'o3', 'temp', 'humidity']],
    # REMOVE THE column_config DICTIONARY ENTIRELY
    hide_index=True,
    use_container_width=True
)