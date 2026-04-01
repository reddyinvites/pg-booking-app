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
# SHEETS
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
VERIFIED_ID = "191Fg2-jLtpvziqFrUdQNV2ki1iXYe_fdTGYv3_Tm7wA"

pg_sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")
verified_sheet = client.open_by_key(VERIFIED_ID).worksheet("verified_pg")

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
# CATEGORY UPLOAD
# -----------------------
st.subheader("📸 Upload by Category")

room_files = st.file_uploader("🛏 Room", accept_multiple_files=True, key="room")
bath_files = st.file_uploader("🚿 Bath", accept_multiple_files=True, key="bath")
food_files = st.file_uploader("🍛 Food", accept_multiple_files=True, key="food")
dining_files = st.file_uploader("🍽 Dining", accept_multiple_files=True, key="dining")
storage_files = st.file_uploader("🗄 Storage", accept_multiple_files=True, key="storage")
outside_files = st.file_uploader("🏡 Outside", accept_multiple_files=True, key="outside")

# -----------------------
# VIDEO UPLOAD
# -----------------------
st.subheader("🎥 Upload Videos")
video_files = st.file_uploader("Videos", accept_multiple_files=True)

# -----------------------
# SAVE
# -----------------------
if st.button("💾 Save PG"):

    def upload_and_tag(files, category):
        urls = []
        if files:
            for f in files:
                res = cloudinary.uploader.upload(f)
                urls.append(res["secure_url"])
        return f"{category}:" + ",".join(urls) if urls else ""

    parts = []

    for data in [
        upload_and_tag(room_files, "room"),
        upload_and_tag(bath_files, "bath"),
        upload_and_tag(food_files, "food"),
        upload_and_tag(dining_files, "dining"),
        upload_and_tag(storage_files, "storage"),
        upload_and_tag(outside_files, "outside"),
    ]:
        if data:
            parts.append(data)

    final_images = "|".join(parts)

    video_urls = []
    if video_files:
        for file in video_files:
            res = cloudinary.uploader.upload(file, resource_type="video")
            video_urls.append(res["secure_url"])

    verified_sheet.append_row([
        name,
        location,
        verified,
        final_images,
        "|".join(video_urls)
    ])

    st.success("✅ Saved Successfully")
    st.session_state.clear()
    st.rerun()

# -----------------------
# TABS
# -----------------------
tab1, tab2 = st.tabs(["📋 PG List", "🖼 Gallery"])

# -----------------------
# TAB 1
# -----------------------
with tab1:
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

        if col1.button("❌ Delete", key=f"d{i}"):
            verified_sheet.delete_rows(i + 2)
            st.rerun()

        if pg.get("verified") != "Yes":
            if col2.button("🔄 Verify", key=f"v{i}"):
                verified_sheet.update_cell(i + 2, 3, "Yes")
                st.rerun()

        st.divider()

# -----------------------
# TAB 2 (GALLERY)
# -----------------------
with tab2:
    st.header("🖼 PG Gallery")

    data = verified_sheet.get_all_records()

    for pg in data:
        st.subheader(pg.get("name"))

        images_raw = str(pg.get("images", "")).split("|")

        for block in images_raw:
            if ":" in block:
                category, urls = block.split(":")
                urls = urls.split(",")

                st.write(f"### {category.upper()}")

                cols = st.columns(3)
                for i, img in enumerate(urls):
                    if img.startswith("http"):
                        cols[i % 3].image(img, use_container_width=True)

        videos = str(pg.get("videos", "")).split("|")

        for v in videos:
            if v.startswith("http"):
                st.video(v)

        st.divider()