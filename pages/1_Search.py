"""Natural-language search page."""

from pathlib import Path

import streamlit as st

from photo_search.config import settings
from photo_search.database import initialize_database, search_photos
from photo_search.embeddings import combined_text_embedding, text_embedding
from photo_search.query_processing import expand_query, parse_search_query
from photo_search.ui import apply_styles

st.set_page_config(page_title="Search | Photo Search", layout="wide")
apply_styles()
st.title("Search your gallery")
st.caption("Describe the scene. Optional date phrases are extracted before semantic search.")

try:
    initialize_database()
except Exception:
    st.error("Could not connect to PostgreSQL. Start the database and check your .env settings.")
    st.stop()

query = st.text_input(
    "What are you looking for?",
    placeholder="Sunset at the beach in 2024",
)
controls = st.columns([1, 1, 2])
with controls[0]:
    amount = st.slider("Results", min_value=1, max_value=30, value=12)
with controls[1]:
    use_expansion = st.checkbox("Expand query with synonyms", value=False)
with controls[2]:
    filter_by_date = st.checkbox("Add a manual date range", value=False)

start_date = end_date = None
if filter_by_date:
    date_range = st.date_input(
        "Manual capture date range",
        value=(),
        help="This can be combined with a year or date found in your search text.",
    )
    if len(date_range) == 2:
        start_date, end_date = date_range
    elif len(date_range) == 1:
        start_date = end_date = date_range[0]
submitted = st.button("Search photos", type="primary")

if submitted:
    if not query.strip():
        st.warning("Enter a description to search.")
    else:
        plan = parse_search_query(query)
        final_start = max(filter(None, (plan.start_date, start_date)), default=None)
        final_end = min(filter(None, (plan.end_date, end_date)), default=None)
        if plan.date_expression:
            st.info(
                f"Date phrase detected: **{plan.date_expression}** "
                f"({plan.start_date} to {plan.end_date}). Searching for: **{plan.semantic_query}**"
            )
        if final_start and final_end and final_start > final_end:
            st.error("The natural-language date and manual date range do not overlap.")
            st.stop()

        variants = expand_query(plan.semantic_query)
        if use_expansion:
            st.caption("Query variants used: " + " | ".join(variants))
        try:
            with st.spinner("Finding the closest photos..."):
                vector = (
                    combined_text_embedding(variants)
                    if use_expansion
                    else text_embedding(plan.semantic_query)
                )
                results = search_photos(vector, amount, final_start, final_end)
            if not results:
                st.info("No matching photos found. Add photos, or try a broader date range or description.")
            else:
                st.subheader(f"{len(results)} matching photos")
                columns = st.columns(4)
                for index, result in enumerate(results):
                    image_path = settings.image_dir / Path(result["stored_name"]).name
                    with columns[index % len(columns)]:
                        with st.container(border=True):
                            if image_path.is_file():
                                st.image(str(image_path), use_container_width=True)
                                captured = result["captured_date"]
                                date_label = f"Captured {captured}" if captured else "Date unknown"
                                st.caption(
                                    f"{result['similarity']:.1%} similarity  |  {date_label}"
                                )
                            else:
                                st.warning("An indexed image file is missing.")
        except Exception:
            st.error("Search failed. Check the model download, database, and image storage.")
