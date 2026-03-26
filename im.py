import streamlit as st
import folium
from streamlit_folium import st_folium
import ee

ee.Initialize()

# Pune boundary
districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
pune = districts.filter(
    ee.Filter.And(
        ee.Filter.eq('ADM0_NAME','India'),
        ee.Filter.eq('ADM1_NAME','Maharashtra'),
        ee.Filter.eq('ADM2_NAME','Pune')
    )
)

# LULC image example
lulc =  ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990").clip(pune)

# Create folium map
m = folium.Map(location=[18.52, 73.85], zoom_start=9)

# Convert LULC to folium tile
map_id_dict = ee.Image(lulc).getMapId({
    'min':0,
    'max':3,
    'palette':['blue','red','gray','green']
})

folium.TileLayer(
    tiles=map_id_dict['tile_fetcher'].url_format,
    attr='Google Earth Engine',
    name='LULC 1990',
    overlay=True,
    control=True
).add_to(m)

# Add Pune boundary
folium.GeoJson(
    data=pune.getInfo(),
    name='Pune Boundary',
    style_function=lambda x: {'fillColor': 'none', 'color':'black', 'weight':2}
).add_to(m)

# Render map in Streamlit
st.subheader("LULC Map for 1990")
st_data = st_folium(m, width=700, height=500)