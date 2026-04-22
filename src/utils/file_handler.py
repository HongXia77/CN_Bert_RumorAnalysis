from io import BytesIO
from pathlib import Path
import uuid

from fastapi import UploadFile
from PIL import Image, ImageOps


BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "avatars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def _thumbnail(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    resample = getattr(Image, "Resampling", Image).LANCZOS
    image.thumbnail((200, 200), resample)
    return image


async def save_avatar(file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return None, "仅支持 JPG/PNG 格式"

    file_name = f"{uuid.uuid4()}{ALLOWED_CONTENT_TYPES[file.content_type]}"
    file_path = UPLOAD_DIR / file_name

    try:
        content = await file.read()
        image = Image.open(BytesIO(content))
        image = _thumbnail(image)

        if file.content_type == "image/jpeg":
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(file_path, format="JPEG", optimize=True, quality=85)
        else:
            if image.mode == "P":
                image = image.convert("RGBA")
            image.save(file_path, format="PNG", optimize=True)

        return f"/static/uploads/avatars/{file_name}", None
    except Exception as exc:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        return None, str(exc)
