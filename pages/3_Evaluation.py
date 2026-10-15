"""Create a small relevance-labeled set and compare retrieval quality."""

from uuid import UUID
from pathlib import Path

import streamlit as st

from photo_search.config import settings
from photo_search.database import (
    initialize_database,
    list_evaluation_cases,
    list_photos,
    save_evaluation_case,
    search_photos,
)
from photo_search.embeddings import combined_text_embedding, text_embedding
from photo_search.query_processing import expand_query, parse_search_query
from photo_search.ui import apply_styles

st.set_page_config(page_title="Evaluation | Photo Search", layout="wide")
apply_styles()
st.title("Evaluate search quality")
st.caption("Label relevant photos for a few queries, then compare CLIP with and without synonym expansion.")

try:
    initialize_database()
    photos = list_photos()
    cases = list_evaluation_cases()
except Exception:
    st.error("Could not connect to PostgreSQL. Start the database and check your .env settings.")
    st.stop()

if not photos:
    st.info("Add and index photos before building an evaluation set.")
    st.stop()

existing_queries = [case["query"] for case in cases]
case_lookup = {case["query"]: case for case in cases}
selected_example = st.selectbox(
    "Load an existing query to edit (optional)", ["New query", *existing_queries]
)
if st.button("Load selected example", disabled=selected_example == "New query"):
    chosen = case_lookup[selected_example]
    st.session_state["evaluation_query"] = chosen["query"]
    st.session_state["evaluation_relevant_ids"] = set(chosen["relevant_photo_ids"])
    st.session_state["_previous_evaluation_query"] = chosen["query"]
    for photo in photos:
        st.session_state[f"relevant_{photo['id']}"] = (
            photo["id"] in st.session_state["evaluation_relevant_ids"]
        )


def clear_labels_for_new_query() -> None:
    query_value = st.session_state.get("evaluation_query", "")
    previous = st.session_state.get("_previous_evaluation_query", "")
    if query_value != previous:
        for photo_id in st.session_state.get("_evaluation_photo_ids", []):
            st.session_state.pop(f"relevant_{photo_id}", None)
        st.session_state["evaluation_relevant_ids"] = set()
        st.session_state["_previous_evaluation_query"] = query_value


st.session_state["_evaluation_photo_ids"] = [photo["id"] for photo in photos]

query = st.text_input(
    "Test query",
    placeholder="Sunset at the beach in 2024",
    max_chars=300,
    key="evaluation_query",
    on_change=clear_labels_for_new_query,
)
plan = parse_search_query(query) if query.strip() else None
if plan and plan.date_expression:
    st.info(f"This query will also apply {plan.date_expression}: {plan.start_date} to {plan.end_date}.")

candidate_photos = photos
if plan and plan.start_date:
    candidate_photos = [
        photo
        for photo in photos
        if photo["captured_date"] is not None
        and plan.start_date <= photo["captured_date"] <= plan.end_date
    ]
    st.caption("Only photos eligible under the parsed date filter are shown for labeling.")

selected_ids = st.session_state.get("evaluation_relevant_ids", set())
st.subheader("Choose the relevant photos")
if not candidate_photos:
    st.warning("No indexed photos match this query's date range.")
else:
    columns = st.columns(4)
    for index, photo in enumerate(candidate_photos):
        key = f"relevant_{photo['id']}"
        if key not in st.session_state:
            st.session_state[key] = photo["id"] in selected_ids
        image_path = settings.image_dir / Path(photo["stored_name"]).name
        with columns[index % len(columns)]:
            with st.container(border=True):
                if image_path.is_file():
                    st.image(str(image_path), use_container_width=True)
                else:
                    st.warning("Image file is missing")
                label = str(photo["captured_date"]) if photo["captured_date"] else "Date unknown"
                st.caption(label)
                st.checkbox("Relevant", key=key)

save_col, _ = st.columns([1, 3])
with save_col:
    save_clicked = st.button("Save labels", type="primary", disabled=not query.strip())
if save_clicked:
    relevant_ids = [
        UUID(photo["id"])
        for photo in candidate_photos
        if st.session_state.get(f"relevant_{photo['id']}", False)
    ]
    if not relevant_ids:
        st.warning("Select at least one relevant photo before saving this query.")
    else:
        try:
            save_evaluation_case(query.strip(), relevant_ids)
            st.session_state["evaluation_relevant_ids"] = {str(photo_id) for photo_id in relevant_ids}
            st.success("Saved the relevance labels.")
        except Exception:
            st.error("Could not save labels to PostgreSQL.")

st.divider()
st.subheader("Compare retrieval")
st.write("Recall@1 and Recall@5 measure how many labeled relevant photos appear near the top. MRR rewards a relevant result appearing earlier.")
cases = list_evaluation_cases()
if not cases:
    st.info("Save relevance labels for a few queries to build the evaluation set.")
elif st.button("Run evaluation", type="primary"):
    rows = []
    baseline_totals = {"Recall@1": 0.0, "Recall@5": 0.0, "MRR": 0.0}
    expanded_totals = {"Recall@1": 0.0, "Recall@5": 0.0, "MRR": 0.0}
    with st.spinner("Running retrieval for each labeled query..."):
        for case in cases:
            parsed = parse_search_query(case["query"])
            relevant = set(case["relevant_photo_ids"])
            baseline = search_photos(
                text_embedding(parsed.semantic_query), 5, parsed.start_date, parsed.end_date
            )
            variants = expand_query(parsed.semantic_query)
            expanded = search_photos(
                combined_text_embedding(variants), 5, parsed.start_date, parsed.end_date
            )

            def score(results: list[dict]) -> dict[str, float]:
                ranked_ids = [item["id"] for item in results]
                first_rank = next(
                    (rank for rank, image_id in enumerate(ranked_ids, start=1) if image_id in relevant),
                    None,
                )
                return {
                    "Recall@1": len(set(ranked_ids[:1]) & relevant) / len(relevant),
                    "Recall@5": len(set(ranked_ids[:5]) & relevant) / len(relevant),
                    "MRR": 1.0 / first_rank if first_rank else 0.0,
                }

            baseline_score = score(baseline)
            expanded_score = score(expanded)
            for metric in baseline_totals:
                baseline_totals[metric] += baseline_score[metric]
                expanded_totals[metric] += expanded_score[metric]
            rows.append(
                {
                    "Query": case["query"],
                    "Baseline R@1": baseline_score["Recall@1"],
                    "Expanded R@1": expanded_score["Recall@1"],
                    "Baseline R@5": baseline_score["Recall@5"],
                    "Expanded R@5": expanded_score["Recall@5"],
                    "Baseline MRR": baseline_score["MRR"],
                    "Expanded MRR": expanded_score["MRR"],
                }
            )

    count = len(cases)
    baseline_average = {name: value / count for name, value in baseline_totals.items()}
    expanded_average = {name: value / count for name, value in expanded_totals.items()}
    metric_columns = st.columns(3)
    for column, name in zip(metric_columns, baseline_average):
        column.metric(
            name,
            f"{expanded_average[name]:.3f}",
            delta=f"{expanded_average[name] - baseline_average[name]:+.3f} vs baseline",
        )
    st.caption("Metric values above show synonym expansion; the delta compares it with plain CLIP.")
    st.dataframe(rows, use_container_width=True, hide_index=True)

if cases:
    st.caption(f"Evaluation set: {len(cases)} labeled query/queries")
