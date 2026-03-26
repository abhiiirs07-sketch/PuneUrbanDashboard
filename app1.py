import streamlit as st
import ee

# Load service account from secrets
service_account_info = st.secrets["EARTHENGINE"]

credentials = ee.ServiceAccountCredentials(
    service_account_info["client_email"],
    key_file=None,
    private_key=service_account_info["private_key"]
)
ee.Initialize(credentials)
