import streamlit as st
import ee
import os
import json
import geemap

st.set_page_config(layout="wide", page_title="Pune LULC Dashboard")

# -----------------------------
# 1. Initialize GEE with service account
# -----------------------------
# Read the service account JSON from environment variable
key_str = os.environ.get("EARTHENGINE_PRIVATE_KEY", None)
if key_str is None:
    st.error("EARTHENGINE_PRIVATE_KEY not found! Upload it as a Streamlit secret.")
    st.stop()

# Replace literal newlines with actual newlines if needed
key_str = key_str.replace("\\n", "\n")

# Parse JSON
try:
    service_account_info = json.loads(key_str)
except json.JSONDecodeError:
    st.error("Invalid EARTHENGINE_PRIVATE_KEY format. Ensure it's valid JSON.")
    st.stop()

# Initialize credentials
credentials = ee.ServiceAccountCredentials(
    service_account_email=service_account_info["client_email"],
    private_key=service_account_info["private_key"]
)
ee.Initialize(credentials)

# -----------------------------
# 2. Define ROI (Pune District)
# -----------------------------
districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
pune = districts.filter(
    ee.Filter.And(
        ee.Filter.eq('ADM0_NAME','India'),
        ee.Filter.eq('ADM1_NAME','Maharashtra'),
        ee.Filter.eq('ADM2_NAME','Pune')
    )
)
center = pune.geometry().centroid().coordinates().getInfo()[::-1]

# -----------------------------
# 3. Create interactive map
# -----------------------------
m = geemap.Map(center=center, zoom=10)
m.add_basemap("HYBRID")

# Load LULC 2010 image as an example
lulc_2010 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010")
vis_params = {"min":1, "max":4, "palette":["blue","red","gray","green"]}
m.addLayer(lulc_2010.clip(pune), vis_params, "LULC 2010")

# Display in Streamlit
m.to_streamlit(height=600)