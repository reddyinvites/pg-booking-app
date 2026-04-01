import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

st.set_page_config(page_title="PG Admin", layout="wide")

# -----------------------
# CONFIG
# -----------------------
cloudinary.config(
    cloud_name=st.secrets["cloudinary"]["cloud_name"],
    api_key=st.secrets["cloudinary"]["api_key"],
    api_secret=st.secrets["cloudinary"]["api_secret"]
)

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

gcp_info = dict(st.secrets["gcp_service_account"])
gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(gcp_info, scopes=scope)
client = gspread.authorize(creds)

# -----------------------
# SHEETS (FINAL FIX)
# -----------------------
SPREADSHEET_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

sheet = client.open_by_key(SPREADSHEET_ID)

pg_data_sheet = sheet.worksheet("Sheet1")        # ✅ YOUR REAL DATA
verified_sheet = sheet.worksheet("verified_pg")  # ✅ SAVE HERE

# -----------------------
# LOGIN
# -----------------------
st.title("👨‍💼 Admin")

password = st.text_input("Password", type="password")

if password != "1234":
    st.stop()

st.success("Logged in")

# -----------------------
# READ PG DATA
# -----------------------
pg_rows = pg_data_sheet.get_all_values()

options = []
for row in pg_rows[1:]:
    if len(row) >= 3:
        name = row[1].strip()
        location = row[2].strip()

        if name and location:
            options.append(f"{name} | {location}")

if not options:
    st.error("❌ No PG data found (Check Sheet1 & sharing)")
    st.stop()

# -----------------------
# ADD PG
# -----------------------
st.header("➕ Add PG")

selected = st.selectbox("Select PG", options)

name, location = selected.split(" | ")

st.text_input("Name", value=name, disabled=True)
st.text_input("Location", value=location, disabled=True)

verified = st.selectbox("Verified", ["Yes", "No"])

# -----------------------
# UPLOAD
# -----------------------
st.subheader("📸 Upload Images")
image_files = st.file_uploader("Images", accept_multiple_files=True)

st.subheader("🎥 Upload Videos")
video_files = st.file_uploader("Videos", accept_multiple_files=True)

image_urls = []
video_urls = []

# Upload images
if image_files:
    for file in image_files:
        res = cloudinary.uploader.upload(file)
        image_urls.append(res["secure_url"])

# Upload videos
if video_files:
    for file in video_files:
        res = cloudinary.uploader.upload(file, resource_type="video")
        video_urls.append(res["secure_url"])

# -----------------------
# SAVE
# -----------------------
if st.button("💾 Save PG"):

    verified_sheet.append_row([
        name,
        location,
        verified,
        "|".join(image_urls),
        "|".join(video_urls)
    ])

    st.success("✅ Saved Successfully")
    st.rerun()

# -----------------------
# MANAGE PGS
# -----------------------
st.header("📋 Manage PGs")

data = verified_sheet.get_all_records()

for i, pg in enumerate(data):

    st.subheader(f"🏠 {pg.get('name')}")
    st.write(f"📍 {pg.get('location')}")

    if pg.get("verified") == "Yes":
        st.success("✅ Verified")
    else:
        st.warning("❌ Not Verified")

    col1, col2 = st.columns(2)

    # DELETE
    if col1.button("❌ Delete", key=f"delete{i}"):
        verified_sheet.delete_rows(i + 2)
        st.rerun()

    # TOGGLE VERIFY
    if pg.get("verified") != "Yes":
        if col2.button("🔄 Toggle Verify", key=f"toggle{i}"):
            verified_sheet.update_cell(i + 2, 3, "Yes")
            st.rerun()

    # -----------------------
    # GALLERY
    # -----------------------
    images = str(pg.get("images", "")).split("|")

    if images:
        cols = st.columns(3)
        for j, img in enumerate(images):
            if img.startswith("http"):
                cols[j % 3].image(img, use_container_width=True)

    videos = str(pg.get("videos", "")).split("|")

    for v in videos:
        if v.startswith("http"):
            st.video(v)

    st.divider()