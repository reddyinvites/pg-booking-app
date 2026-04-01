import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.title("DEBUG CONNECTION")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

gcp_info = dict(st.secrets["gcp_service_account"])
gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(gcp_info, scopes=scope)
client = gspread.authorize(creds)

sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")

st.success("✅ Connected")

# Test Sheet1
ws = sheet.worksheet("Sheet1")
rows = ws.get_all_values()

st.write("📊 DATA:", rows)