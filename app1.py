import streamlit as st
import ee
import json
import tempfile

# Load service account from secrets
service_account_info = st.secrets["EARTHENGINE"]

# Save the JSON temporarily
with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
    json.dump(service_account_info, f)
    f.flush()  # ensure it's written
    credentials = ee.ServiceAccountCredentials.from_json_keyfile_name(f.name)

# Initialize Earth Engine
ee.Initialize(credentials)

st.success("✅ Earth Engine initialized successfully")