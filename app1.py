# app.py
import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import os
import tempfile

# ---------------------------
# 1️⃣ Initialize GEE with Service Account
# ---------------------------
SERVICE_ACCOUNT = "abhiiirs07@jarvice-ng.iam.gserviceaccount.com"

# Load JSON key from environment variable (cloud secret)
json_content = os.environ.get("EARTHENGINE_PRIVATE_KEY")

# Fallback: use local JSON for testing
if json_content is None:
    try:
        with open("service_account.json") as f:
            json_content = f.read()
    except FileNotFoundError:
        st.error("GEE credentials not found. Set EARTHENGINE_PRIVATE_KEY or upload service_account.json")
        st.stop()

# Write JSON content to temporary file
with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
    f.write(json_content)
    key_file_path = f.name

# Initialize Earth Engine
credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, key_file_path)
ee.Initialize(credentials)

# ---------------------------
# 2️⃣ LULC Images and Classes
# ---------------------------
lulc_images = {
    1990: ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990"),
    2000: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000"),
    2010: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010"),
    2019: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20191"),
    2025: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20251")
}

# LULC classes
class_dict = {0: "Built-up", 1: "Vegetation", 2: "Water", 3: "Barren"}
palette = {0: "red", 1: "green", 2: "blue", 3: "gray"}

# Pune boundary
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
# 3️⃣ Functions
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
        area_km2 = area.getInfo()[list(area.getInfo().keys())[0]]/1e6
        areas[class_dict[cls]] = area_km2
    return areas

def render_map(folium_map):
    map_html = folium_map.to_html()
    components.html(map_html, height=500)

# ---------------------------
# 4️⃣ Streamlit UI
# ---------------------------
st.set_page_config(page_title="Urbangrowth Development Dashboard", layout="wide")
st.title("🏙️ Pune Urban Growth Dashboard")

# Sidebar
st.sidebar.header("Settings")
year = st.sidebar.selectbox("Select Year", [1990, 2000, 2010, 2019, 2025])
compare_btn = st.sidebar.checkbox("Compare 1990 vs 2025 (Swipe Slider)")

# ---------------------------
# 5️⃣ Display Map
# ---------------------------
st.subheader(f"LULC Map for {year}")
m = geemap.Map(center=[18.52,73.85], zoom=9)
vis_params = {'min':0,'max':len(class_dict)-1,'palette':[palette[k] for k in sorted(palette.keys())]}
m.addLayer(get_lulc_layer(year), vis_params, f"LULC {year}")
m.addLayer(pune, {}, "Boundary")
render_map(m)

# ---------------------------
# 6️⃣ Legend
# ---------------------------
st.markdown("**Legend:**")
cols = st.columns(len(class_dict))
for i, cls in enumerate(class_dict.keys()):
    with cols[i]:
        st.markdown(f"<div style='background-color:{palette[cls]};width:100%;height:25px;border:1px solid black'></div>", unsafe_allow_html=True)
        st.markdown(f"**{class_dict[cls]}**", unsafe_allow_html=True)

# ---------------------------
# 7️⃣ Area Table
# ---------------------------
areas = calculate_area(year)
st.subheader(f"LULC Area for {year} (sq.km)")
st.table(pd.DataFrame(list(areas.items()), columns=['Class', 'Area (sq.km)']))

# ---------------------------
# 8️⃣ Stacked Area Chart
# ---------------------------
st.subheader("LULC Trends Over Time")
years = [1990, 2000, 2010, 2019, 2025]
lulc_areas_all = {cls: [calculate_area(y)[cls] for y in years] for cls in class_dict.values()}

fig_area = go.Figure()
for cls in class_dict.values():
    fig_area.add_trace(go.Scatter(
        x=years,
        y=lulc_areas_all[cls],
        mode='lines',
        stackgroup='one',
        name=cls,
        line=dict(width=0.5),
        fillcolor=palette[[k for k,v in class_dict.items() if v==cls][0]]
    ))
fig_area.update_layout(
    title="LULC Area Trends Over Time",
    xaxis_title="Year",
    yaxis_title="Area (sq.km)"
)
st.plotly_chart(fig_area, use_container_width=True)

# ---------------------------
# 9️⃣ Swipe Comparison
# ---------------------------
if compare_btn:
    st.subheader("Swipe Comparison: 1990 vs 2025")
    layer1 = get_lulc_layer(1990)
    layer2 = get_lulc_layer(2025)
    m_swipe = geemap.Map(center=[18.52,73.85], zoom=9)
    m_swipe.addLayer(layer1, vis_params, "1990 LULC")
    m_swipe.addLayer(layer2, vis_params, "2025 LULC")
    m_swipe.addLayer(pune, {}, "Boundary")
    m_swipe.to_streamlit(height=500, swipe=True)