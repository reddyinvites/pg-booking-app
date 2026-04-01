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
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
VERIFIED_ID = "191Fg2-jLtpvziqFrUdQNV2ki1iXYe_fdTGYv3_Tm7wA"

pg_sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")          # pg_data file
verified_sheet = client.open_by_key(VERIFIED_ID).worksheet("verified_pg")  # ✅ FIXED

# -----------------------
# LOGIN
# -----------------------
st.title("👨‍💼 Admin Panel")

password = st.text_input("Password", type="password")

if password != "1234":
    st.stop()

st.success("✅ Logged in")

# -----------------------
# READ PG DATA
# -----------------------
pg_rows = pg_sheet.get_all_values()

options = []
for row in pg_rows[1:]:
    if len(row) >= 3:
        name = row[1].strip()
        location = row[2].strip()

        if name and location:
            options.append(f"{name} | {location}")

if not options:
    st.error("❌ No PG data found")
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

# -----------------------
# SAVE
# -----------------------
if st.button("💾 Save PG"):

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
# MANAGE PGs
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
    if col1.button("❌ Delete", key=f"d{i}"):
        verified_sheet.delete_rows(i + 2)
        st.rerun()

    # VERIFY
    if pg.get("verified") != "Yes":
        if col2.button("🔄 Verify", key=f"v{i}"):
            verified_sheet.update_cell(i + 2, 3, "Yes")
            st.rerun()

    # -----------------------
    # IMAGES
    # -----------------------
    images = str(pg.get("images", "")).split("|")

    valid_images = [img for img in images if img.startswith("http")]

    if valid_images:
        st.write("📸 Images")
        cols = st.columns(3)
        for j, img in enumerate(valid_images):
            cols[j % 3].image(img, use_container_width=True)

    # -----------------------
    # VIDEOS
    # -----------------------
    videos = str(pg.get("videos", "")).split("|")

    valid_videos = [v for v in videos if v.startswith("http")]

    if valid_videos:
        st.write("🎥 Videos")
        for v in valid_videos:
            st.video(v)

    st.divider()