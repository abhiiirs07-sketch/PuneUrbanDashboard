import streamlit as st
import geemap  # instead of geemap.foliumap
import ee
import json

# --- Initialize Earth Engine ---
key_str = st.secrets["EARTHENGINE"]["PRIVATE_KEY"]
service_account_info = json.loads(key_str)

credentials = ee.ServiceAccountCredentials(
    service_account_info["client_email"],
    key_file=None,
    token_uri=service_account_info["token_uri"],
    private_key=service_account_info["private_key"]
)
ee.Initialize(credentials)

st.title("Pune Urban Growth Dashboard")

# --- Map ---
Map = geemap.Map(center=[18.5204, 73.8567], zoom=10)
Map.add_basemap("HYBRID")

st.components.v1.html(Map.to_html(), height=600)