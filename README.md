# Photo Search: text-to-image search over your gallery

Search your own photos with natural-language descriptions. CLIP maps images and text into a shared embedding space; PostgreSQL with pgvector ranks photos by cosine similarity. The app runs locally with a dark Streamlit interface.

## What it can do

- Upload JPEG, PNG, and WebP photos in Streamlit.
- Search by scene meaning, without relying on filenames or manual tags.
- Extract a date from common query phrases, including years, year ranges, month/year, full dates, and relative phrases such as `last month`.
- Optionally expand a query with a small, transparent English synonym map. The original query stays in the embedding average, and the UI displays the generated variants.
- Filter by a manually selected capture-date range.
- Build a relevance-labeled evaluation set and compare plain CLIP with synonym expansion using Recall@1, Recall@5, and MRR.

## Requirements

- Windows, macOS, or Linux
- Python 3.10 or newer
- Docker Desktop or Docker Engine with Docker Compose
- Internet access on the first model load to download `openai/clip-vit-base-patch32`
- No GPU required; the app works on CPU and uses CUDA when it is available

## Setup on Windows PowerShell

1. Create the local environment file and set a strong local password. The two password values must match:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   `.env` is excluded from Git. Do not commit it.

2. Start PostgreSQL with pgvector in Docker:

   ```powershell
   docker compose up -d
   docker compose ps
   ```

   The database uses the `pgvector/pgvector:0.8.7-pg16-trixie` image. The app creates or updates its tables when it connects.

3. Create a Python environment and install the packages:

   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   Use an installed Python version of 3.10 or newer in place of `3.13` if needed.

4. Start the app:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py
   ```

   Open the local URL printed by Streamlit. On first use, CLIP must download, which can take a few minutes.

5. Use **Add Photos** to index images, **Search** to find them, and **Evaluation** to label examples and compare retrieval metrics.

## Database port conflicts

Docker publishes PostgreSQL on `127.0.0.1:5432` by default. If Windows reports that port 5432 is unavailable or reserved, change **both** values in `.env` to the same free port, for example:

```env
POSTGRES_PORT=5433
DB_PORT=5433
```

Then run `docker compose up -d` again. `POSTGRES_PORT` is the port on your computer; PostgreSQL still listens on port 5432 inside the container. `DB_PORT` tells the Streamlit app which host port to use.

## Using date search

The app reads the photo's EXIF capture date during upload, before removing embedded metadata from the saved image copy. Search queries can include phrases such as:

```text
sunset at the beach in 2024
friends between 2023 and 2024
beach in June 2024
photos on 2024-06-15
photos from last month
```

Photos without an EXIF capture date remain searchable when no date filter is active, but they cannot match a date filter. In Windows File Explorer, check **Properties → Details → Date taken**; **Date created** only tells you when the file was saved on that computer. Reupload original files indexed before date support to populate any available dates. Exact duplicate files are not added again.

## Query expansion

On the Search page, enable **Expand query with synonyms** to create alternate phrasings. The built-in map currently includes terms such as `dog/puppy`, `beach/shore/seaside`, `ocean/sea`, `forest/woods`, `cake/dessert`, and `festival/celebration`. The app batches and averages the normalized text embeddings. Expansion may help some searches and hurt others; it is optional and can be switched off.

## Building an evaluation set

1. Upload a varied set of photos, including similar-looking distractors (for example, beach sunsets and city sunsets).
2. Open **Evaluation** in the sidebar.
3. Enter a test query and select every photo that should count as relevant. Save the labels.
4. Repeat for at least 8–10 queries. To revise labels, load a saved query, update the selections, and save again.
5. Click **Run evaluation** to compare plain CLIP with synonym expansion.

Recall@k is the fraction of labeled relevant photos found in the top k results. MRR is the reciprocal rank of the first relevant result. The displayed scores are averaged across labeled queries. The evaluation table is stored in PostgreSQL and created automatically when the Evaluation page connects.

For example, label queries such as `dog playing in grass`, `puppy in the park`, `sunset at the beach`, `college students at a festival`, `ocean waves`, and `sunset at the beach in 2024`. Queries with dates only consider photos whose capture date falls in the parsed range.

## Photo and database storage

- Uploaded photos are decoded, orientation-corrected, and re-encoded as JPEG with generated filenames in `data/images/`.
- Original filenames and EXIF metadata are not stored in the normalized image copies. PostgreSQL stores the SHA-256 upload hash, generated filename, optional capture date, and 512-dimensional CLIP embedding.
- The database port is bound to localhost by default. The app is intended for local use and does not include user accounts or remote access controls.
- Docker stores database files in the named `postgres_data` volume. `docker compose down` stops the database without removing data. `docker compose down -v` deletes the database and evaluation labels; photos in `data/images/` remain.

## Troubleshooting

- **Port 5432 unavailable:** Set `POSTGRES_PORT` and `DB_PORT` to the same free port, such as `5433`, in `.env`, then run `docker compose up -d` again.
- **Database connection error:** Check `docker compose ps`, confirm the database is healthy, and ensure the `DB_*` values in `.env` match the database settings.
- **No date-filtered results:** Confirm that the original image has a **Date taken** value in EXIF. File creation time is not used as a substitute.
- **Model loading takes a while:** The first load downloads CLIP. Later runs use the local model cache.

## Project structure

```text
app.py                         Home page and navigation cards
pages/1_Search.py              Semantic search, date parsing, query expansion
pages/2_Add_Photos.py          Upload and index photos
pages/3_Evaluation.py          Relevance labeling and retrieval metrics
photo_search/config.py         Environment-backed settings
photo_search/database.py       PostgreSQL and pgvector operations
photo_search/embeddings.py     CLIP image/text embeddings
photo_search/image_store.py    Upload validation and EXIF date extraction
photo_search/query_processing.py  Date parsing and synonym expansion
photo_search/ui.py             Shared dark theme styling
sql/init.sql                   pgvector and table setup
docker-compose.yml             PostgreSQL with pgvector
.streamlit/config.toml         Streamlit dark theme configuration
data/images/                   Locally stored sanitized photo files
```
