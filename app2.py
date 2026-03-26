# app.py
import streamlit as st
import ee
# import geemap.foliumap as geemap
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import geemap
m = geemap.Map()
# ---------------------------
# Initialize GEE
# ---------------------------
ee.Initialize()

# ---------------------------
# 1. Load LULC Images
# ---------------------------
lulc_images = {
    1990: ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990"),
    2000: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000"),
    2019: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20191"),
    2025: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20251")
}

# ---------------------------
# 2. LULC Classes
# ---------------------------
# Your classes: Water, Built-up, Barren, Vegetation
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
        # Get first key (band name)
        area_km2 = list(area.getInfo().values())[0] / 1e6
        areas[class_dict[cls]] = area_km2
    return areas

# ---------------------------
# 5. Streamlit UI
# ---------------------------
st.set_page_config(page_title="Pune Urban Dashboard", layout="wide")
st.title("🏙️ Pune Urban Growth Dashboard")

# Sidebar
st.sidebar.header("Settings")
year = st.sidebar.selectbox("Select Year", [1990, 2000, 2019, 2025])
compare_btn = st.sidebar.checkbox("Compare 1990 vs 2025 (Swipe Slider)")

# ---------------------------
# 6. Display Map
# ---------------------------
st.subheader(f"LULC Map for {year}")
m = geemap.Map(center=[18.52,73.85], zoom=9)
vis_params = {'min':0,'max':len(class_dict)-1,'palette':[palette[k] for k in sorted(palette.keys())]}
m.addLayer(get_lulc_layer(year), vis_params, f"LULC {year}")
m.addLayer(pune, {}, "Boundary")

# Render interactive map
m.to_streamlit(height=500)

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
# 9. Graphs
# ---------------------------
st.subheader("Urban Growth Trend Graphs")
years = [1990, 2000, 2019, 2025]
builtup_areas = [calculate_area(y)["Built-up"] for y in years]

# Line chart
fig_line = px.line(x=years, y=builtup_areas, markers=True,
                   labels={'x':'Year','y':'Built-up Area (sq.km)'},
                   title="Built-up Growth Over Time")
st.plotly_chart(fig_line, use_container_width=True)

# Bar chart
fig_bar = px.bar(x=years, y=builtup_areas, labels={'x':'Year','y':'Built-up Area (sq.km)'},
                 title="Built-up Area Bar Chart", color=builtup_areas, color_continuous_scale='Reds')
st.plotly_chart(fig_bar, use_container_width=True)

# Pie chart for selected year
labels = list(areas.keys())
values = list(areas.values())
fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
fig_pie.update_layout(title=f"LULC Distribution {year}")
st.plotly_chart(fig_pie, use_container_width=True)


# ---------------------------
# 11. Multi-class Stacked Area Chart
# ---------------------------
st.subheader("LULC Area Trend (All Classes)")

# Prepare data
lulc_trend = []
for y in years:
    areas_y = calculate_area(y)
    areas_y['Year'] = y
    lulc_trend.append(areas_y)

df_trend = pd.DataFrame(lulc_trend)
df_trend = df_trend[['Year'] + list(class_dict.values())]  # Ensure order: Year, Water, Built-up, Barren, Vegetation

# Plot stacked area chart
fig_area = go.Figure()
for cls in class_dict.values():
    fig_area.add_trace(go.Scatter(
        x=df_trend['Year'],
        y=df_trend[cls],
        mode='lines',
        stackgroup='one',
        name=cls
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
# 10. Swipe Comparison
# ---------------------------
if compare_btn:
    st.subheader("Swipe Comparison: 1990 vs 2025")
    layer1 = get_lulc_layer(1990)
    layer2 = get_lulc_layer(2025)
    m_swipe = geemap.Map(center=[18.52,73.85], zoom=9)
    m_swipe.addLayer(layer1, vis_params, "1990 LULC")
    m_swipe.addLayer(layer2, vis_params, "2025 LULC")
    m_swipe.addLayer(pune, {}, "Boundary")
    # Enable swipe
    m_swipe.to_streamlit(height=500, swipe=True)


# ---------------------------
# 11. Multi-class Stacked Area Chart (Color-coded)
# ---------------------------
st.subheader("LULC Area Trend (All Classes)")

# Prepare data
lulc_trend = []
for y in years:
    areas_y = calculate_area(y)
    areas_y['Year'] = y
    lulc_trend.append(areas_y)

df_trend = pd.DataFrame(lulc_trend)
df_trend = df_trend[['Year'] + list(class_dict.values())]  # Ensure order: Year, Water, Built-up, Barren, Vegetation

# Define color palette to match map legend
color_palette = {
    "Water": "blue",
    "Built-up": "red",
    "Barren": "gray",
    "Vegetation": "green"
}

# Plot stacked area chart
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