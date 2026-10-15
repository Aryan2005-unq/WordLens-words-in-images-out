"""Home page for the personal photo search app."""

import streamlit as st

from photo_search.ui import apply_styles

st.set_page_config(page_title="Photo Search", layout="wide")
apply_styles()

st.title("Photo Search")
st.markdown(
    "### Find the moment you remember\n"
    "Search your gallery with ordinary descriptions. CLIP matches the meaning of your "
    "words to your photos, and date phrases can narrow results automatically."
)

links = st.columns(3)
with links[0]:
    with st.container(border=True):
        st.subheader("Search photos")
        st.write("Describe a scene, people, or moment in your gallery.")
        st.page_link("pages/1_Search.py", label="Open search")
with links[1]:
    with st.container(border=True):
        st.subheader("Add photos")
        st.write("Upload JPEG, PNG, or WebP images and index them with CLIP.")
        st.page_link("pages/2_Add_Photos.py", label="Open uploads")
with links[2]:
    with st.container(border=True):
        st.subheader("Evaluate search")
        st.write("Label relevant photos and compare retrieval metrics.")
        st.page_link("pages/3_Evaluation.py", label="Open evaluation")

st.divider()
st.caption(
    "Photo files remain in the local data/images folder. PostgreSQL stores their "
    "embeddings, capture dates, and generated filenames."
)
