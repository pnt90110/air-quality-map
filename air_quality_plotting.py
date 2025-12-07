import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np

# --- 1. Basic Setup and Data Loading ---

# Set the page configuration for a wider layout
st.set_page_config(layout="wide", page_title="Current Air Quality Map")

# Use st.cache_data to load the CSV only once for performance
@st.cache_data
def load_data():
    """Loads and returns the clean air quality data."""
    # Ensure this file name matches your clean CSV file exactly
    file_path = 'AQI_Thailand_FINAL_DATA_20251207_142243.csv'
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found.")
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
    min_value=pm25_min,
    max_value=pm25_max,
    value=pm25_min, # Default: show all
    step=1.0
)

# Apply PM2.5 filter
df_filtered = df_filtered[df_filtered['pm25'] >= pm25_threshold]

# --- 4. Geospatial Map Visualization (Plotly Express) ---

st.header("Air Quality Map (Color and Size by AQI)")

# Check if there's data to plot after filtering
if not df_filtered.empty:
    
    # Create the scatter_mapbox figure using Plotly Express
    fig = px.scatter_mapbox(
        df_filtered,
        lat="latitude",
        lon="longitude",
        color="aqi_overall",            # Color the points by overall AQI
        size="pm25",                     # Size the points by PM2.5 concentration
        hover_name="city_name",          # Show city name on hover
        hover_data={
            "pm25": ':.1f',              # Format PM2.5 in tooltip
            "aqi_overall": True,
            "latitude": False,
            "longitude": False,
            "temp": ':.1f',              # Include temperature in tooltip
        },
        color_continuous_scale=px.colors.sequential.Sunsetdark, # Use a clear color scale
        zoom=5,                         # Initial zoom level (adjust based on region)
        height=600,
    )
    
    # Update map style and layout
    # Requires a free Mapbox token for other styles, but 'open-street-map' works by default
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    
    # Display the Plotly chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)
    

else:
    st.warning("No stations match the selected filter criteria. Try reducing the minimum PM2.5 threshold.")

# --- 5. Data Table Preview ---

st.markdown("---")
st.header("Filtered Data Table")
st.caption(f"Showing {len(df_filtered)} of {len(df)} records.")
st.dataframe(df_filtered[['city_name', 'time_utc', 'aqi_overall', 'pm25', 'pm10', 'o3', 'temp', 'humidity']])