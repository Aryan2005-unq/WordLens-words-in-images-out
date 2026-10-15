"""CLIP model loading and normalized image/text embedding generation."""

import streamlit as st
import torch
import torch.nn.functional as functional
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from photo_search.config import settings


@st.cache_resource(show_spinner="Loading CLIP model (first run downloads it)...")
def load_clip() -> tuple[CLIPModel, CLIPProcessor, torch.device]:
    """Load one shared model, using CUDA if available and CPU otherwise."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = CLIPProcessor.from_pretrained(settings.model_id)
    model = CLIPModel.from_pretrained(settings.model_id)
    model.to(device)
    model.eval()
    return model, processor, device


def image_embedding(image: Image.Image) -> list[float]:
    model, processor, device = load_clip()
    inputs = processor(images=image, return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        vector = model.get_image_features(**inputs)
        vector = functional.normalize(vector, p=2, dim=-1)
    return vector[0].float().cpu().tolist()


def text_embeddings(texts: list[str]) -> list[list[float]]:
    """Encode several text variants in one CLIP batch."""
    model, processor, device = load_clip()
    inputs = processor(
        text=texts, return_tensors="pt", padding=True, truncation=True
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        vector = model.get_text_features(**inputs)
        vector = functional.normalize(vector, p=2, dim=-1)
    return vector.float().cpu().tolist()


def text_embedding(text: str) -> list[float]:
    return text_embeddings([text])[0]


def combined_text_embedding(texts: list[str]) -> list[float]:
    """Average normalized embeddings for a query and its expanded variants."""
    vectors = torch.tensor(text_embeddings(texts), dtype=torch.float32)
    combined = functional.normalize(vectors.mean(dim=0), p=2, dim=0)
    return combined.tolist()
