import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

st.set_page_config(page_title="PG Admin", layout="wide")

# -----------------------
# 🎨 FONT + UI STYLE
# -----------------------
st.markdown("""
<style>
html, body, [class*="css"]  {
    font-family: 'Poppins', sans-serif;
}
h1, h2, h3 {
    color: #1f2937;
}
</style>
""", unsafe_allow_html=True)

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
# MENU
# -----------------------
menu = st.radio("Menu", ["➕ Add PG", "📋 PG List", "🖼 Gallery"])

# -----------------------
# ADD PG
# -----------------------
if menu == "➕ Add PG":

    pg_rows = pg_sheet.get_all_values()

    options = []
    for row in pg_rows[1:]:
        if len(row) >= 3:
            name = row[1].strip()
            location = row[2].strip()
            if name and location:
                options.append(f"{name}|{location}")

    selected = st.selectbox("Select PG", options)

    name, location = selected.split("|")

    st.text_input("Name", value=name, disabled=True)
    st.text_input("Location", value=location, disabled=True)

    verified = st.selectbox("Verified", ["Yes", "No"])

    # -----------------------
    # CATEGORY UPLOAD
    # -----------------------
    categories = ["room", "bath", "food", "dining", "storage", "outside"]

    category_data = {}

    for cat in categories:
        st.subheader(f"📸 {cat.upper()}")
        files = st.file_uploader(cat, accept_multiple_files=True, key=cat)
        category_data[cat] = files

    st.subheader("🎥 Videos")
    video_files = st.file_uploader("videos", accept_multiple_files=True)

    # -----------------------
    # SAVE
    # -----------------------
    if st.button("💾 Save PG"):

        # ❌ DUPLICATE CHECK
        existing = verified_sheet.get_all_records()
        for row in existing:
            if row.get("name") == name:
                st.error("❌ Already uploaded this PG")
                st.stop()

        all_category_urls = []

        # Upload category images
        for cat, files in category_data.items():
            urls = []
            if files:
                for file in files:
                    res = cloudinary.uploader.upload(file)
                    urls.append(res["secure_url"])

            if urls:
                all_category_urls.append(f"{cat}:{','.join(urls)}")

        # Upload videos
        video_urls = []
        if video_files:
            for file in video_files:
                res = cloudinary.uploader.upload(file, resource_type="video")
                video_urls.append(res["secure_url"])

        verified_sheet.append_row([
            name,
            location,
            verified,
            "|".join(all_category_urls),
            "|".join(video_urls)
        ])

        st.success("✅ Saved Successfully")

        # 🔄 CLEAR FORM
        st.session_state.clear()
        st.rerun()

# -----------------------
# PG LIST
# -----------------------
if menu == "📋 PG List":

    st.header("📋 PG List")

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
            if col2.button("✔ Verify", key=f"v{i}"):
                verified_sheet.update_cell(i + 2, 3, "Yes")
                st.rerun()

        st.divider()

# -----------------------
# GALLERY
# -----------------------
if menu == "🖼 Gallery":

    st.header("🖼 PG Gallery")

    data = verified_sheet.get_all_records()

    for pg in data:
        st.markdown(f"## 🏠 {pg.get('name')}")
        st.caption(f"📍 {pg.get('location')}")

        images_raw = str(pg.get("images", "")).split("|")

        for block in images_raw:
            if ":" in block:
                category, urls = block.split(":", 1)
                urls = urls.split(",")

                st.markdown(f"### 🔹 {category.upper()}")

                cols = st.columns(3)

                for i, img in enumerate(urls):
                    if img.startswith("http"):
                        with cols[i % 3]:
                            st.image(img, use_container_width=True)

        # VIDEOS
        videos = str(pg.get("videos", "")).split("|")

        valid_videos = [v for v in videos if v.startswith("http")]

        if valid_videos:
            st.markdown("### 🎥 VIDEOS")
            for v in valid_videos:
                st.video(v)

        st.markdown("---")