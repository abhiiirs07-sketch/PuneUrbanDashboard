import streamlit as st
import ee
import os
import json
import geemap

# Read secret
key_str = st.secrets["general"]["EARTHENGINE_PRIVATE_KEY"]

# Convert escaped newlines to actual newlines
key_str = key_str.replace("\\n", "\n")

# Parse JSON
service_account_info = json.loads(key_str)

# Initialize credentials
credentials = ee.ServiceAccountCredentials(
    service_account_info["client_email"],
    service_account_info["private_key"]
)
ee.Initialize(credentials)

st.success("Earth Engine initialized successfully ✅")