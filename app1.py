# app_refactored.py
import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from folium.plugins import DualMap

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
    2010: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010"),
    2019: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20191"),
    2025: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20251")
}

# ---------------------------
# 2. LULC Classes and Palette
# ---------------------------
class_dict = {0: "Water", 1: "Built-up", 2: "Barren", 3: "Vegetation"}
palette = {0: "blue", 1: "red", 2: "gray", 3: "green"}
pixel_area = ee.Image.pixelArea()

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

# ---------------------------
# 4. Functions
# ---------------------------
def get_lulc_layer(year):
    return lulc_images[year].clip(pune)

def calculate_area(year):
    """
    Optimized area calculation: sum all classes in one reduceRegion call.
    Returns dict {class_name: area_km2}.
    """
    img = lulc_images[year]
    # Create one-hot images for each class
    class_masks = [img.eq(cls).rename(str(cls)) for cls in class_dict.keys()]
    combined = ee.Image.cat(class_masks).multiply(pixel_area)
    
    # Reduce region once
    areas = combined.reduceRegion(
        reducer=ee.Reducer.sum().unweighted(),
        geometry=pune,
        scale=30,
        maxPixels=1e13
    ).getInfo()
    
    return {class_dict[int(k)]: v / 1e6 for k, v in areas.items()}

def render_folium_map(lulc_image, vis_palette, title="LULC Map", overlay_image=None, overlay_opacity=0.6):
    """
    Returns folium map with optional overlay for swipe/comparison.
    """
    m = folium.Map(location=[18.52, 73.85], zoom_start=9)
    
    # Base layer
    map_id = ee.Image(lulc_image).getMapId({
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
    
    # Overlay layer (optional)
    if overlay_image:
        overlay_id = ee.Image(overlay_image).getMapId({
            'min': 0,
            'max': len(vis_palette)-1,
            'palette': [vis_palette[k] for k in sorted(vis_palette.keys())]
        })
        folium.TileLayer(
            tiles=overlay_id['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name='Overlay',
            overlay=True,
            control=True,
            opacity=overlay_opacity
        ).add_to(m)
    
    # Pune boundary
    folium.GeoJson(
        data=pune.getInfo(),
        name='Pune Boundary',
        style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
    ).add_to(m)
    
    return m

def generate_dynamic_legend(palette_dict):
    """
    Generates HTML legend for Streamlit dynamically.
    """
    cols = st.columns(len(palette_dict))
    for i, (cls, color) in enumerate(palette_dict.items()):
        with cols[i]:
            st.markdown(
                f"<div style='background-color:{color};width:100%;height:25px;border:1px solid black'></div>",
                unsafe_allow_html=True
            )
            st.markdown(f"**{cls}**", unsafe_allow_html=True)

# ---------------------------
# 5. Streamlit UI
# ---------------------------
st.set_page_config(page_title="Pune Urban Dashboard", layout="wide")
st.title("🏙️ Pune Urban Growth Dashboard")

# Sidebar settings
st.sidebar.header("Settings")
year = st.sidebar.slider("Select Year", 1990, 2025, 2019, step=1)
compare_btn = st.sidebar.checkbox("Compare 1990 vs 2025 (Swipe Slider)")

# ---------------------------
# 6. Display LULC Map
# ---------------------------
st.subheader(f"LULC Map for {year}")
m = render_folium_map(get_lulc_layer(year), palette, title=f"LULC {year}")
st_folium(m, width=700, height=500)

# ---------------------------
# 7. Dynamic Legend
# ---------------------------
st.markdown("**Legend:**")
generate_dynamic_legend({v: palette[k] for k, v in class_dict.items()})

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
fig_line = px.line(
    x=years, y=builtup_areas, markers=True,
    labels={'x':'Year','y':'Built-up Area (sq.km)'},
    title="Built-up Growth Over Time"
)
st.plotly_chart(fig_line, use_container_width=True)

# Bar chart
fig_bar = px.bar(
    x=years, y=builtup_areas,
    labels={'x':'Year','y':'Built-up Area (sq.km)'},
    title="Built-up Area Bar Chart",
    color=builtup_areas,
    color_continuous_scale='Reds'
)
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
    st.subheader("Swipe Comparison: 1990 vs 2025 (DualMap)")
    m_dual = DualMap(location=[18.52, 73.85], zoom_start=9)
    
    # Map 1: 1990
    map1_id = ee.Image(get_lulc_layer(1990)).getMapId({
        'min': 0, 'max': len(palette)-1,
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
        style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
    ).add_to(m_dual.m1)
    
    # Map 2: 2025
    map2_id = ee.Image(get_lulc_layer(2025)).getMapId({
        'min': 0, 'max': len(palette)-1,
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
        style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
    ).add_to(m_dual.m2)
    
    st_folium(m_dual, width=900, height=500)