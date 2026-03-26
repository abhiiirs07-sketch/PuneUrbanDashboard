# app.py
import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import ee
import streamlit as st

# Initialize Earth Engine using Streamlit secrets
service_account = st.secrets["client_email"]
private_key = st.secrets["private_key"]

credentials = ee.ServiceAccountCredentials(
    service_account,
    key_data={
        "client_email": service_account,
        "private_key": private_key
    }
)

ee.Initialize(credentials)

# ---------------------------
# Initialize Google Earth Engine
# ---------------------------
ee.Initialize()

# ---------------------------
# 1. Load LULC Images
# ---------------------------
lulc_images = {
    1990: ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990"),
    2000: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000"),
    2010: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010"),  # New 2010 asset
    2019: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20191"),
    2025: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20251")
}

# ---------------------------
# 2. LULC Classes and Palette
# ---------------------------
class_dict = {0: "Water", 1: "Built-up", 2: "Barren", 3: "Vegetation"}
palette = {0: "blue", 1: "red", 2: "gray", 3: "green"}

# ---------------------------
# 3. Pune Boundary
# ---------------------------
districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
pune = districts.filter(
    ee.Filter.And(
        ee.Filter.eq('ADM0_NAME','India'),
        ee.Filter.eq('ADM1_NAME','Maharashtra'),
        ee.Filter.eq('ADM2_NAME','Pune')
    )
)
pixel_area = ee.Image.pixelArea()

# ---------------------------
# 4. Functions
# ---------------------------
def get_lulc_layer(year):
    return lulc_images[year].clip(pune)

def calculate_area(year):
    img = lulc_images[year]
    areas = {}
    for cls in class_dict.keys():
        mask = img.eq(cls)
        area = mask.multiply(pixel_area).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=pune,
            scale=30,
            maxPixels=1e13
        )
        area_km2 = list(area.getInfo().values())[0] / 1e6
        areas[class_dict[cls]] = area_km2
    return areas

def render_folium_map(lulc_image, vis_palette, title="LULC Map"):
    """Render LULC image on folium map for Streamlit."""
    m = folium.Map(location=[18.52, 73.85], zoom_start=9)
    
    # Add LULC tile layer
    map_id_dict = ee.Image(lulc_image).getMapId({
        'min':0,
        'max':len(vis_palette)-1,
        'palette':[vis_palette[k] for k in sorted(vis_palette.keys())]
    })
    
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=title,
        overlay=True,
        control=True
    ).add_to(m)
    
    # Add Pune boundary
    folium.GeoJson(
        data=pune.getInfo(),
        name='Pune Boundary',
        style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
    ).add_to(m)
    
    return m

# ---------------------------
# 5. Streamlit UI
# ---------------------------
st.set_page_config(page_title="Pune Urban Dashboard", layout="wide")
st.title("🏙️ Pune Urban Growth Dashboard")

# Sidebar
st.sidebar.header("Settings")
year = st.sidebar.selectbox("Select Year", [1990, 2000, 2010, 2019, 2025])
compare_btn = st.sidebar.checkbox("Compare 1990 vs 2025 (Swipe Slider)")

# ---------------------------
# 6. Display LULC Map
# ---------------------------
st.subheader(f"LULC Map for {year}")
m = render_folium_map(get_lulc_layer(year), palette, title=f"LULC {year}")
st_data = st_folium(m, width=700, height=500)

# ---------------------------
# 7. Legend
# ---------------------------
st.markdown("**Legend:**")
cols = st.columns(len(class_dict))
for i, cls in enumerate(class_dict.keys()):
    with cols[i]:
        st.markdown(f"<div style='background-color:{palette[cls]};width:100%;height:25px;border:1px solid black'></div>", unsafe_allow_html=True)
        st.markdown(f"**{class_dict[cls]}**", unsafe_allow_html=True)

# ---------------------------
# 8. Area Table
# ---------------------------
areas = calculate_area(year)
st.subheader(f"LULC Area for {year} (sq.km)")
st.table(pd.DataFrame(list(areas.items()), columns=['Class', 'Area (sq.km)']))

# ---------------------------
# 9. Built-up Graphs
# ---------------------------
st.subheader("Built-up Growth Trend Graphs")
years = [1990, 2000, 2010, 2019, 2025]
builtup_areas = [calculate_area(y)["Built-up"] for y in years]

# Line chart
fig_line = px.line(x=years, y=builtup_areas, markers=True,
                   labels={'x':'Year','y':'Built-up Area (sq.km)'},
                   title="Built-up Growth Over Time")
st.plotly_chart(fig_line, use_container_width=True)

# Bar chart
fig_bar = px.bar(x=years, y=builtup_areas,
                 labels={'x':'Year','y':'Built-up Area (sq.km)'},
                 title="Built-up Area Bar Chart",
                 color=builtup_areas,
                 color_continuous_scale='Reds')
st.plotly_chart(fig_bar, use_container_width=True)

# Pie chart for selected year
labels = list(areas.keys())
values = list(areas.values())
fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
fig_pie.update_layout(title=f"LULC Distribution {year}")
st.plotly_chart(fig_pie, use_container_width=True)

# ---------------------------
# 10. Multi-class Stacked Area Chart
# ---------------------------
st.subheader("LULC Area Trend (All Classes)")
lulc_trend = []
for y in years:
    areas_y = calculate_area(y)
    areas_y['Year'] = y
    lulc_trend.append(areas_y)

df_trend = pd.DataFrame(lulc_trend)
df_trend = df_trend[['Year'] + list(class_dict.values())]

# Correct mapping: class names -> colors
color_palette = {v: palette[k] for k, v in class_dict.items()}

fig_area = go.Figure()
for cls in class_dict.values():
    fig_area.add_trace(go.Scatter(
        x=df_trend['Year'],
        y=df_trend[cls],
        mode='lines',
        stackgroup='one',
        name=cls,
        line=dict(width=0.5),
        fillcolor=color_palette[cls]
    ))

fig_area.update_layout(
    title="Stacked Area Chart of LULC Classes Over Time",
    xaxis_title="Year",
    yaxis_title="Area (sq.km)",
    legend_title="LULC Class",
    hovermode="x unified"
)

st.plotly_chart(fig_area, use_container_width=True)

# ---------------------------
# 11. Swipe Comparison (Optional)
# ---------------------------
if compare_btn:
    st.subheader("Swipe Comparison: 1990 vs 2025")
    # Base layer: 1990
    m1 = render_folium_map(get_lulc_layer(1990), palette, title="1990 LULC")
    # Overlay: 2025 with opacity
    map_id_dict2 = ee.Image(get_lulc_layer(2025)).getMapId({
        'min':0,
        'max':len(palette)-1,
        'palette':[palette[k] for k in sorted(palette.keys())]
    })
    folium.TileLayer(
        tiles=map_id_dict2['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name='2025 LULC',
        overlay=True,
        control=True,
        opacity=0.6
    ).add_to(m1)
    st_folium(m1, width=700, height=500)
# ---------------------------
# 11. Swipe Comparison with draggable slider
# ---------------------------
if compare_btn:
    st.subheader("Swipe Comparison: 1990 vs 2025 (Draggable)")

    from folium.plugins import DualMap

    # Create a DualMap (two maps side-by-side)
    m_dual = DualMap(location=[18.52, 73.85], zoom_start=9)

    # Map 1: 1990
    map1_id = ee.Image(get_lulc_layer(1990)).getMapId({
        'min':0,
        'max':len(palette)-1,
        'palette':[palette[k] for k in sorted(palette.keys())]
    })
    folium.TileLayer(
        tiles=map1_id['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name='1990 LULC',
        overlay=True,
        control=True
    ).add_to(m_dual.m1)

    folium.GeoJson(
        data=pune.getInfo(),
        name='Pune Boundary',
        style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
    ).add_to(m_dual.m1)

    # Map 2: 2025
    map2_id = ee.Image(get_lulc_layer(2025)).getMapId({
        'min':0,
        'max':len(palette)-1,
        'palette':[palette[k] for k in sorted(palette.keys())]
    })
    folium.TileLayer(
        tiles=map2_id['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name='2025 LULC',
        overlay=True,
        control=True
    ).add_to(m_dual.m2)

    folium.GeoJson(
        data=pune.getInfo(),
        name='Pune Boundary',
        style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
    ).add_to(m_dual.m2)

    st_folium(m_dual, width=900, height=500)