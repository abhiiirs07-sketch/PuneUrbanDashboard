# app.py
import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------
# 0. Earth Engine Auth
# ---------------------------
# Make sure you put your service account JSON in Streamlit secrets:
# [EARTHENGINE]
# type = "service_account"
# project_id = "jarvice-ng"
# private_key_id = "..."
# private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
# client_email = "..."
# client_id = "..."
# auth_uri = "..."
# token_uri = "..."
# auth_provider_x509_cert_url = "..."
# client_x509_cert_url = "..."
# universe_domain = "googleapis.com"

service_account_info = st.secrets["EARTHENGINE"]

# Initialize Earth Engine
credentials = ee.ServiceAccountCredentials.from_json_keyfile_dict(service_account_info)
ee.Initialize(credentials)

st.success("✅ Earth Engine initialized successfully")

# ---------------------------
# 1. Load LULC Images
# ---------------------------
lulc_images = {
    1990: ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990"),
    2000: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000"),
    2010: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010"),
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
        ee.Filter.eq('ADM0_NAME', 'India'),
        ee.Filter.eq('ADM1_NAME', 'Maharashtra'),
        ee.Filter.eq('ADM2_NAME', 'Pune')
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
    areas_dict = img.multiply(0).add(img).reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=pune,
        scale=30,
        maxPixels=1e13
    ).getInfo()
    hist = areas_dict.get('classification', areas_dict)  # depends on band name
    areas_km2 = {}
    for cls_val, name in class_dict.items():
        count = hist.get(str(cls_val), 0)
        areas_km2[name] = (count * 900) / 1e6  # 30m x 30m = 900 m²
    return areas_km2

def render_map(image, vis_palette, title="LULC Map"):
    m = folium.Map(location=[18.52, 73.85], zoom_start=9)
    map_id = ee.Image(image).getMapId({
        'min': 0,
        'max': len(vis_palette)-1,
        'palette': [vis_palette[k] for k in sorted(vis_palette.keys())]
    })
    folium.TileLayer(
        tiles=map_id['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=title,
        overlay=True,
        control=True
    ).add_to(m)
    folium.GeoJson(
        data=pune.getInfo(),
        name='Pune Boundary',
        style_function=lambda x: {'fillColor': 'none','color':'black','weight':2}
    ).add_to(m)
    return m

# ---------------------------
# 5. Streamlit UI
# ---------------------------
st.set_page_config(page_title="Pune LULC Dashboard", layout="wide")
st.title("🏙️ Pune Urban Growth Dashboard")

# Sidebar
st.sidebar.header("Settings")
year = st.sidebar.slider("Select Year", min_value=1990, max_value=2025, step=1, value=2019)
compare_btn = st.sidebar.checkbox("Compare 1990 vs 2025")

# Map
st.subheader(f"LULC Map: {year}")
m = render_map(get_lulc_layer(year), palette)
st_folium(m, width=700, height=500)

# Dynamic legend
st.markdown("**Legend:**")
cols = st.columns(len(class_dict))
for i, cls in enumerate(class_dict.keys()):
    with cols[i]:
        st.markdown(
            f"<div style='background-color:{palette[cls]};width:100%;height:25px;border:1px solid black'></div>"
            f"**{class_dict[cls]}**",
            unsafe_allow_html=True
        )

# Area Table
areas = calculate_area(year)
st.subheader(f"LULC Area ({year}) in sq.km")
st.table(pd.DataFrame(list(areas.items()), columns=["Class","Area (sq.km)"]))

# Built-up trends
st.subheader("Built-up Area Trend")
years = [1990, 2000, 2010, 2019, 2025]
builtup_areas = [calculate_area(y)["Built-up"] for y in years]
fig_line = px.line(x=years, y=builtup_areas, markers=True,
                   labels={'x':'Year','y':'Built-up Area (sq.km)'},
                   title="Built-up Growth")
st.plotly_chart(fig_line, use_container_width=True)

# Optional Swipe
if compare_btn:
    st.subheader("Swipe 1990 vs 2025")
    from folium.plugins import DualMap
    m_dual = DualMap(location=[18.52, 73.85], zoom_start=9)
    # Left map: 1990
    map1_id = ee.Image(get_lulc_layer(1990)).getMapId({
        'min':0,'max':len(palette)-1,
        'palette':[palette[k] for k in sorted(palette.keys())]
    })
    folium.TileLayer(tiles=map1_id['tile_fetcher'].url_format,
                     attr='Google Earth Engine',
                     name='1990 LULC').add_to(m_dual.m1)
    folium.GeoJson(data=pune.getInfo(), name='Pune Boundary',
                   style_function=lambda x:{'fillColor':'none','color':'black','weight':2}).add_to(m_dual.m1)
    # Right map: 2025
    map2_id = ee.Image(get_lulc_layer(2025)).getMapId({
        'min':0,'max':len(palette)-1,
        'palette':[palette[k] for k in sorted(palette.keys())]
    })
    folium.TileLayer(tiles=map2_id['tile_fetcher'].url_format,
                     attr='Google Earth Engine',
                     name='2025 LULC').add_to(m_dual.m2)
    folium.GeoJson(data=pune.getInfo(), name='Pune Boundary',
                   style_function=lambda x:{'fillColor':'none','color':'black','weight':2}).add_to(m_dual.m2)
    st_folium(m_dual, width=900, height=500)