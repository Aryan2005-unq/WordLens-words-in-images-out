"""Upload and index photos page."""

from uuid import uuid4

import streamlit as st
from PIL import Image

from photo_search.config import settings
from photo_search.database import add_photo, initialize_database
from photo_search.embeddings import image_embedding
from photo_search.image_store import InvalidImageError, save_upload
from photo_search.ui import apply_styles

st.set_page_config(page_title="Add Photos | Photo Search", layout="wide")
apply_styles()
st.title("Add photos to your gallery")
st.write("Add a batch of photos. The app validates and re-encodes each image before indexing it.")
st.caption(f"JPEG, PNG, and WebP - up to {settings.max_upload_mb} MB per image")
st.info("Capture dates are read from EXIF when available. Reupload older originals to add dates without creating duplicates.")

uploads = st.file_uploader(
    "Choose photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
)

if uploads and st.button("Index photos", type="primary"):
    try:
        initialize_database()
    except Exception:
        st.error("Could not connect to PostgreSQL. Start the database and check your .env settings.")
        st.stop()

    progress = st.progress(0, text="Preparing uploads...")
    indexed = duplicates = failures = 0
    for position, upload in enumerate(uploads, start=1):
        destination = None
        try:
            destination, stored_name, digest, captured_date = save_upload(upload)
            with Image.open(destination) as image:
                prepared = image.convert("RGB")
                try:
                    embedding = image_embedding(prepared)
                finally:
                    prepared.close()
            inserted = add_photo(
                uuid4(), stored_name, digest, embedding, captured_date
            )
            if inserted:
                indexed += 1
            else:
                destination.unlink(missing_ok=True)
                duplicates += 1
        except InvalidImageError as exc:
            failures += 1
            st.warning(f"{upload.name}: {exc}")
        except Exception:
            failures += 1
            if destination is not None:
                destination.unlink(missing_ok=True)
            st.warning(f"Could not index {upload.name}; check model, database, or storage availability.")
        progress.progress(position / len(uploads), text=f"Processed {position} of {len(uploads)}")

    st.success(f"Added {indexed} photo(s). Skipped {duplicates} duplicate(s); {failures} failed.")
    st.info("Open Search from the sidebar to find your photos.")
