import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Verified PGs", layout="wide")

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
sheet = client.open("verified_pg")
pg_sheet = sheet.sheet1

pg_data_sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").sheet1

# -----------------------
# SESSION
# -----------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

# -----------------------
# IMAGE URL
# -----------------------
def get_img_url(public_id):
    return f"https://res.cloudinary.com/{st.secrets['cloudinary']['cloud_name']}/image/upload/{public_id}.jpg"

# -----------------------
# UPLOAD
# -----------------------
def upload(files, folder="pg_images", video=False):
    urls = []

    if files:
        for f in files:
            try:
                res = cloudinary.uploader.upload(
                    f,
                    folder=folder,
                    resource_type="video" if video else "image"
                )

                if video:
                    urls.append(res["secure_url"])
                else:
                    urls.append(res["public_id"])

            except Exception as e:
                st.error(f"Upload failed: {e}")

    return ",".join(urls)

# -----------------------
# HOME (pg_data SOURCE)
# -----------------------
if st.session_state.page == "home":

    st.title("🏠 Verified PGs")

    data = pg_data_sheet.get_all_values()
    rows = data[1:] if len(data) > 1 else []

    for i, row in enumerate(rows):

        if len(row) < 2:
            continue

        name = row[0]
        location = row[1]

        if not name.strip():
            continue

        st.subheader(f"🏠 {name}")
        st.write(f"📍 {location}")

        if st.button(f"View {name}", key=f"view_{i}"):
            st.session_state.pg_name = name
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

    name = st.session_state.pg_name

    data = pg_sheet.get_all_values()
    rows = data[1:] if len(data) > 1 else []

    matched_pg = None

    for row in rows:
        if len(row) >= 1 and row[0] == name:
            matched_pg = row
            break

    if not matched_pg:
        st.warning("No verified data found for this PG")
        if st.button("⬅ Back"):
            st.session_state.page = "home"
            st.rerun()
        st.stop()

    location = matched_pg[1]
    verified = matched_pg[2]
    images = matched_pg[3] if len(matched_pg) > 3 else ""
    videos = matched_pg[4] if len(matched_pg) > 4 else ""

    st.title(name)
    st.write(f"📍 {location}")

    if verified == "Yes":
        st.success("✅ Verified by Us")

    st.markdown("## 📸 Gallery")
    st.divider()

    sections = images.split("|")
    titles = ["🏠 Room", "🚿 Bathroom", "🍛 Food", "🍽️ Dining", "🧳 Storage", "📍 Outside"]

    for idx, sec in enumerate(sections):

        img_list = [img for img in sec.split(",") if img.strip()]

        if img_list:
            st.subheader(titles[idx])

            cols = st.columns(3)

            for i, img in enumerate(img_list):
                cols[i % 3].image(
                    get_img_url(img),
                    use_container_width=True
                )

    video_list = [v for v in videos.split(",") if v.strip()]

    if video_list:
        st.subheader("🎥 Videos")

        cols = st.columns(2)

        for i, vid in enumerate(video_list):
            cols[i % 2].video(vid)

    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()

# -----------------------
# ADMIN (UPDATED DROPDOWN ONLY)
# -----------------------
elif st.session_state.page == "admin":

    st.title("👨‍💼 Admin")

    if st.text_input("Password", type="password") != "1234":
        st.stop()

    st.success("Logged in")

    if st.button("Logout"):
        st.session_state.clear()
        st.session_state.page = "home"
        st.rerun()

    st.subheader("Add PG")

    # 🔥 DROPDOWN FROM pg_data
    pg_data = pg_data_sheet.get_all_values()
    pg_rows = pg_data[1:] if len(pg_data) > 1 else []

    pg_options = []

    for row in pg_rows:
        if len(row) >= 2 and row[0].strip():
            pg_options.append(f"{row[0]} | {row[1]}")

    selected_pg = st.selectbox("Select PG", pg_options)

    name, location = selected_pg.split(" | ")

    verified = st.selectbox("Verified", ["Yes", "No"])

    def uploader(key):
        return st.file_uploader(key, accept_multiple_files=True, key=key)

    room = uploader("room")
    bath = uploader("bath")
    food = uploader("food")
    dining = uploader("dining")
    storage = uploader("storage")
    outside = uploader("outside")
    videos = st.file_uploader("videos", type=["mp4"], accept_multiple_files=True)

    if st.button("Save PG"):

        sections = [
            upload(room),
            upload(bath),
            upload(food),
            upload(dining),
            upload(storage),
            upload(outside)
        ]

        image_string = "|".join([s for s in sections if s])
        video_string = upload(videos, folder="pg_videos", video=True)

        pg_sheet.append_row([
            name.strip(),
            location.strip(),
            verified,
            image_string,
            video_string
        ])

        st.success("Saved!")
        st.rerun()