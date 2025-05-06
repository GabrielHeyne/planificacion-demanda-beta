# utils.py
import streamlit as st
from PIL import Image
import os

def render_logo_sidebar():
    logo_path = os.path.join("planity_logo.png")  # Ruta del logo
    image = Image.open(logo_path)
    st.sidebar.image(image, use_container_width=True)
