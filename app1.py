# app.py
import streamlit as st
import ee
import geemap
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Initialize GEE
ee.Initialize()

# ---------------------------
# 1. Load LULC images
# ---------------------------
lulc_images = {
    1990: ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990"),
    2000: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000"),
    2019: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20191"),
    2025: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20251")
}

# LULC classes
class_dict = {0: "Non-Urban", 1: "Urban", 2: "Vegetation", 3: "Water", 4: "Barren"}
palette = {0: "white", 1: "red", 2: "green", 3: "blue", 4: "gray"}

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
# 2. Functions
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
    # Convert geemap map to HTML and embed in Streamlit
    map_html = folium_map.to_html()
    components.html(map_html, height=500)

# ---------------------------
# 3. Streamlit UI
# ---------------------------
st.set_page_config(page_title="Pune Urban Dashboard", layout="wide")
st.title("🏙️ Pune Urban Growth Dashboard")

# Sidebar
st.sidebar.header("Settings")
year = st.sidebar.selectbox("Select Year", [1990, 2000, 2019, 2025])
compare_btn = st.sidebar.checkbox("Compare 1990 vs 2025 (Swipe Slider)")

# ---------------------------
# 4. Display Map
# ---------------------------
st.subheader(f"LULC Map for {year}")
m = geemap.Map(center=[18.52,73.85], zoom=9)
vis_params = {'min':0,'max':len(class_dict)-1,'palette':[palette[k] for k in sorted(palette.keys())]}
m.addLayer(get_lulc_layer(year), vis_params, f"LULC {year}")
m.addLayer(pune, {}, "Boundary")
render_map(m)

# ---------------------------
# 5. Legend
# ---------------------------
st.markdown("**Legend:**")
cols = st.columns(len(class_dict))
for i, cls in enumerate(class_dict.keys()):
    with cols[i]:
        st.markdown(f"<div style='background-color:{palette[cls]};width:100%;height:25px;border:1px solid black'></div>", unsafe_allow_html=True)
        st.markdown(f"**{class_dict[cls]}**", unsafe_allow_html=True)

# ---------------------------
# 6. Area Table
# ---------------------------
areas = calculate_area(year)
st.subheader(f"LULC Area for {year} (sq.km)")
st.table(pd.DataFrame(list(areas.items()), columns=['Class', 'Area (sq.km)']))

# ---------------------------
# 7. Graphs
# ---------------------------
st.subheader("Urban Growth Trend Graphs")
years = [1990, 2000, 2019, 2025]
urban_areas = [calculate_area(y)["Urban"] for y in years]

# Line chart
fig_line = px.line(x=years, y=urban_areas, markers=True, labels={'x':'Year','y':'Urban Area (sq.km)'}, title="Urban Growth Over Time")
st.plotly_chart(fig_line, use_container_width=True)

# Bar chart
fig_bar = px.bar(x=years, y=urban_areas, labels={'x':'Year','y':'Urban Area (sq.km)'}, title="Urban Area Bar Chart", color=urban_areas, color_continuous_scale='Reds')
st.plotly_chart(fig_bar, use_container_width=True)

# Pie chart
labels = list(areas.keys())
values = list(areas.values())
fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
fig_pie.update_layout(title=f"LULC Distribution {year}")
st.plotly_chart(fig_pie, use_container_width=True)

# ---------------------------
# 8. Swipe Comparison
# ---------------------------
if compare_btn:
    st.subheader("Swipe Comparison: 1990 vs 2025")
    layer1 = get_lulc_layer(1990)
    layer2 = get_lulc_layer(2025)
    m_swipe = geemap.Map(center=[18.52,73.85], zoom=9)
    m_swipe.addLayer(layer1, vis_params, "1990 LULC")
    m_swipe.addLayer(layer2, vis_params, "2025 LULC")
    m_swipe.addLayer(pune, {}, "Boundary")
    
    # Enable side-by-side swipe
    m_swipe.to_streamlit(height=500, swipe=True)