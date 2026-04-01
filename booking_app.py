import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

st.set_page_config(page_title="Verified PGs", layout="wide")

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
verified_sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").sheet1

# 👉 CHANGE THIS (pg_data sheet ID)
pg_data_sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").worksheet("Sheet1")

# -----------------------
# SESSION
# -----------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

# -----------------------
# HOME
# -----------------------
if st.session_state.page == "home":

    st.title("🏠 Verified PGs")

    data = verified_sheet.get_all_records()

    for i, pg in enumerate(data):

        st.subheader(f"🏠 {pg.get('name','')}")
        st.write(f"📍 {pg.get('location','')}")

        if pg.get("verified") == "Yes":
            st.success("✅ Verified")

        if st.button(f"View {pg.get('name')}", key=f"view{i}"):
            st.session_state.pg = pg
            st.session_state.page = "detail"
            st.rerun()

        st.divider()

    if st.button("👨‍💼 Admin"):
        st.session_state.page = "admin"
        st.rerun()

# -----------------------
# DETAIL (GALLERY)
# -----------------------
elif st.session_state.page == "detail":

    pg = st.session_state.pg

    st.title(pg.get("name"))
    st.write(f"📍 {pg.get('location')}")

    st.subheader("📸 Gallery")

    images = str(pg.get("images", "")).split("|")

    cols = st.columns(2)
    for i, img in enumerate(images):
        if img.startswith("http"):
            cols[i % 2].image(img)

    st.subheader("🎥 Videos")

    videos = str(pg.get("videos", "")).split("|")
    for v in videos:
        if v.startswith("http"):
            st.video(v)

    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()

# -----------------------
# ADMIN
# -----------------------
elif st.session_state.page == "admin":

    st.title("👨‍💼 Admin")

    password = st.text_input("Password", type="password")
    if password != "1234":
        st.stop()

    st.success("Logged in")

    # -----------------------
    # DROPDOWN FROM PG_DATA
    # -----------------------
    pg_data = pg_data_sheet.get_all_values()

    options = []

    for row in pg_data[1:]:
        try:
            name = row[1].strip()      # pg_name (B column)
            location = row[2].strip()  # location (C column)

            if name and location:
                options.append(f"{name} | {location}")
        except:
            continue

    if not options:
        st.error("❌ No PG data found")
        st.stop()

    selected = st.selectbox("Select PG", options)

    name, location = selected.split(" | ")

    st.text_input("Name", value=name, disabled=True)
    st.text_input("Location", value=location, disabled=True)

    verified = st.selectbox("Verified", ["Yes", "No"])

    # -----------------------
    # UPLOADS
    # -----------------------
    st.subheader("📸 Images")
    image_files = st.file_uploader("Upload Images", accept_multiple_files=True)

    st.subheader("🎥 Videos")
    video_files = st.file_uploader("Upload Videos", accept_multiple_files=True)

    image_urls = []
    video_urls = []

    if image_files:
        for file in image_files:
            res = cloudinary.uploader.upload(file)
            image_urls.append(res["secure_url"])

    if video_files:
        for file in video_files:
            res = cloudinary.uploader.upload(file, resource_type="video")
            video_urls.append(res["secure_url"])

    # -----------------------
    # SAVE
    # -----------------------
    if st.button("Save PG"):

        verified_sheet.append_row([
            name,
            location,
            verified,
            "|".join(image_urls),
            "|".join(video_urls)
        ])

        st.success("PG Saved ✅")
        st.rerun()

    st.divider()

    # -----------------------
    # MANAGE PGs
    # -----------------------
    st.subheader("📋 Manage PGs")

    data = verified_sheet.get_all_records()

    for i, pg in enumerate(data):

        st.markdown(f"### 🏠 {pg.get('name')}")
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

        # TOGGLE (DISABLE IF VERIFIED)
        if pg.get("verified") != "Yes":
            if col2.button("🔄 Toggle Verify", key=f"t{i}"):
                verified_sheet.update_cell(i + 2, 3, "Yes")
                st.rerun()

        st.divider()