import streamlit as st
import ee
import json
import os
import geemap.foliumap as geemap
import pandas as pd
import altair as alt

st.set_page_config(layout="wide", page_title="Pune LULC Dashboard")

# -----------------------------
# 1️⃣ Initialize GEE with service account
# -----------------------------
service_account_info = json.loads(os.environ["EARTHENGINE_PRIVATE_KEY"])
credentials = ee.ServiceAccountCredentials(
    service_account_email=service_account_info["client_email"],
    private_key=service_account_info["private_key"]
)
ee.Initialize(credentials)

# -----------------------------
# 2️⃣ Define ROI (Pune district)
# -----------------------------
districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
roi = districts.filter(
    ee.Filter.eq('ADM2_NAME', 'Pune')
)
Map_center = roi.geometry().centroid().coordinates().getInfo()[::-1]

# -----------------------------
# 3️⃣ Load LULC assets
# -----------------------------
lulc_1990 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990")
lulc_2000 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000")
lulc_2010 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_2010")
lulc_2019 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_2019")
lulc_2022 = ee.Image("projects/jarvice-ng/assets/Pune_LULC_2022")

lulc_dict = {
    "1990": lulc_1990,
    "2000": lulc_2000,
    "2010": lulc_2010,
    "2019": lulc_2019,
    "2022": lulc_2022
}

# -----------------------------
# 4️⃣ LULC class palette
# -----------------------------
class_names = ["Water", "Built-up", "Barren", "Vegetation"]
color_palette = {
    "Water": "blue",
    "Built-up": "red",
    "Barren": "gray",
    "Vegetation": "green"
}

# -----------------------------
# 5️⃣ Sidebar for year selection
# -----------------------------
st.sidebar.title("LULC Map Options")
year1 = st.sidebar.selectbox("Select First Year", list(lulc_dict.keys()), index=0)
year2 = st.sidebar.selectbox("Select Second Year", list(lulc_dict.keys()), index=3)

# -----------------------------
# 6️⃣ Create Map with draggable swipe
# -----------------------------
m = geemap.Map(center=Map_center, zoom=10)
m.add_basemap("HYBRID")

lulc1 = lulc_dict[year1].clip(roi)
lulc2 = lulc_dict[year2].clip(roi)

vis_params = {"min": 1, "max": 4, "palette": ["blue", "red", "gray", "green"]}

m.addLayer(lulc1, vis_params, f"LULC {year1}")
m.addLayer(lulc2, vis_params, f"LULC {year2}")

# Add a real swipe control
m.addLayerControl()
m.add_control(geemap.SwipeControl(left_layer=lulc1, right_layer=lulc2, orientation="horizontal"))

st.subheader("LULC Map Comparison")
m.to_streamlit(height=600)

# -----------------------------
# 7️⃣ Calculate area per class for all years
# -----------------------------
def calculate_area(image):
    # area in km2 per class
    pixel_area = ee.Image.pixelArea().divide(1e6)
    areas = {}
    for i, cls in enumerate(class_names, start=1):
        mask = image.eq(i)
        area = mask.multiply(pixel_area).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=30,
            maxPixels=1e13
        ).getInfo()
        areas[cls] = area.get('constant', 0) if 'constant' in area else 0
    return areas

area_data = []
for year, img in lulc_dict.items():
    areas = calculate_area(img)
    areas['Year'] = int(year)
    area_data.append(areas)

df_area = pd.DataFrame(area_data)

# -----------------------------
# 8️⃣ Stacked area chart
# -----------------------------
st.subheader("LULC Area Trends (km²)")
df_melt = df_area.melt(id_vars=["Year"], value_vars=class_names, var_name="Class", value_name="Area")

chart = alt.Chart(df_melt).mark_area(opacity=0.6).encode(
    x="Year:O",
    y="Area:Q",
    color=alt.Color("Class:N", scale=alt.Scale(domain=class_names,
                                               range=[color_palette[cls] for cls in class_names])),
    tooltip=["Year", "Class", "Area"]
).interactive()

st.altair_chart(chart, use_container_width=True)

# -----------------------------
# 9️⃣ Display area table
# -----------------------------
st.subheader("LULC Area Table (km²)")
st.dataframe(df_area.style.format("{:.2f}"))

# -----------------------------
# 10️⃣ Footer
# -----------------------------
st.markdown("""
---
**Developed by:** Abhishek | **Project:** Pune Urban LULC Dashboard
""")