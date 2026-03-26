import streamlit as st
import ee
import os
import json
import geemap

st.set_page_config(layout="wide", page_title="Pune LULC Dashboard")

# Initialize GEE
service_account_info = json.loads(os.environ["EARTHENGINE_PRIVATE_KEY"])
credentials = ee.ServiceAccountCredentials(
    service_account_email=service_account_info["client_email"],
    private_key=service_account_info["private_key"]
)
ee.Initialize(credentials)

# Define ROI
districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
roi = districts.filter(ee.Filter.eq('ADM2_NAME', 'Pune'))
center = roi.geometry().centroid().coordinates().getInfo()[::-1]

# Create map using standard geemap.Map (ipyleaflet-based)
m = geemap.Map(center=center, zoom=10)
m.add_basemap("HYBRID")

# Load LULC images
lulc_2010 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010")
vis_params = {"min": 1, "max": 4, "palette": ["blue", "red", "gray", "green"]}
m.addLayer(lulc_2010.clip(roi), vis_params, "LULC 2010")

# Display map in Streamlit
m.to_streamlit(height=600)