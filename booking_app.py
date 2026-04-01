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
# SHEET CONNECT
# -----------------------
SPREADSHEET_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
sheet = client.open_by_key(SPREADSHEET_ID)

verified_sheet = sheet.get_worksheet(0)   # Verified PGs
pg_data_sheet = sheet.get_worksheet(0)    # PG Data (same for now)

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
# DETAIL PAGE
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
            cols[i % 2].image(img, use_container_width=True)

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

    # 🔄 REFRESH BUTTON
    if st.button("🔄 Refresh Data"):
        st.rerun()

    # -----------------------
    # DEBUG (IMPORTANT)
    # -----------------------
    pg_data = pg_data_sheet.get_all_values()
    st.write("DEBUG DATA:", pg_data)  # remove later

    # -----------------------
    # DROPDOWN
    # -----------------------
    options = []

    for row in pg_data[1:]:
        if len(row) >= 3:
            name = str(row[1]).strip()
            location = str(row[2]).strip()

            if name and location:
                options.append(f"{name} | {location}")

    if len(options) == 0:
        st.error("❌ No PG data found (Check sheet sharing)")
        st.stop()

    selected = st.selectbox("Select PG", options)

    name, location = selected.split(" | ")

    st.text_input("Name", value=name, disabled=True)
    st.text_input("Location", value=location, disabled=True)

    verified = st.selectbox("Verified", ["Yes", "No"])

    # -----------------------
    # UPLOAD
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

        if not name:
            st.error("❌ No PG selected")
        else:
            verified_sheet.append_row([
                name,
                location,
                verified,
                "|".join(image_urls),
                "|".join(video_urls)
            ])

            st.success("✅ Saved Successfully")
            st.rerun()

    st.divider()

    # -----------------------
    # MANAGE
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

        if col1.button("❌ Delete", key=f"d{i}"):
            verified_sheet.delete_rows(i + 2)
            st.rerun()

        if pg.get("verified") != "Yes":
            if col2.button("🔄 Verify", key=f"t{i}"):
                verified_sheet.update_cell(i + 2, 3, "Yes")
                st.rerun()

        st.divider()