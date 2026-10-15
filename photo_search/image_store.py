"""Validate uploads and persist sanitized image files."""

from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from photo_search.config import settings

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME_DIGITIZED = 36868
EXIF_DATETIME = 306
Image.MAX_IMAGE_PIXELS = 20_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)


class InvalidImageError(ValueError):
    """Raised when an uploaded file is not an allowed, safe-to-decode image."""


def extract_capture_date(image: Image.Image) -> date | None:
    """Read the best available EXIF capture date, returning None if unavailable."""
    try:
        exif = image.getexif()
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        candidates = (
            exif_ifd.get(EXIF_DATETIME_ORIGINAL),
            exif_ifd.get(EXIF_DATETIME_DIGITIZED),
            exif.get(EXIF_DATETIME),
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return None

    for value in candidates:
        if isinstance(value, str):
            try:
                return datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S").date()
            except ValueError:
                continue
    return None


def save_upload(uploaded_file) -> tuple[Path, str, str, date | None]:
    """Decode, normalize, and save an upload under an unguessable generated name."""
    raw = uploaded_file.getvalue()
    if not raw or len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise InvalidImageError(f"File must be between 1 byte and {settings.max_upload_mb} MB.")

    try:
        with Image.open(BytesIO(raw)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise InvalidImageError("Only JPEG, PNG, and WebP images are supported.")
            probe.verify()
        with Image.open(BytesIO(raw)) as source:
            captured_date = extract_capture_date(source)
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise InvalidImageError("The file is not a valid image or is too large to decode.") from exc

    digest = sha256(raw).hexdigest()
    filename = f"{uuid4().hex}.jpg"
    settings.image_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.image_dir / filename
    temporary = settings.image_dir / f".{filename}.tmp"
    try:
        image.save(temporary, format="JPEG", quality=90, optimize=True)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
        image.close()
    return destination, filename, digest, captured_date
