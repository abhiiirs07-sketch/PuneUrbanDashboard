import os
import json
import streamlit as st
import ee
import geemap.foliumap as geemap  # or geemap.eefolium

# --- Initialize Earth Engine using the service account ---
try:
    # Load the service account JSON from Streamlit secrets
    key_str = st.secrets["EARTHENGINE"]["PRIVATE_KEY"]
    service_account_info = json.loads(key_str)

    # Authenticate using the service account info
    credentials = ee.ServiceAccountCredentials(
        service_account_info["client_email"], key_file=None, token_uri=service_account_info["token_uri"], private_key=service_account_info["private_key"]
    )
    ee.Initialize(credentials)
except Exception as e:
    st.error(f"Failed to initialize Earth Engine: {e}")
    st.stop()

st.title("Pune Urban Growth Dashboard")

# --- Example map ---
Map = geemap.Map(center=[18.5204, 73.8567], zoom=10)
Map.add_basemap("HYBRID")
st.components.v1.html(Map.to_html(), height=600)