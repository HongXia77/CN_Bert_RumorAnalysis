import os
from PIL import Image
from fastapi import UploadFile
import uuid

UPLOAD_DIR = "static/uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_avatar(file: UploadFile):
    # 1. 验证文件类型
    if file.content_type not in ["image/jpeg", "image/png"]:
        return None, "仅支持 JPG/PNG 格式"

    # 2. 生成唯一文件名防止覆盖
    extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    # 3. 图像处理 (优化与调整尺寸)
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        with Image.open(file_path) as img:
            # 统一调整为 200x200 的缩略图
            img.thumbnail((200, 200))
            img.save(file_path, optimize=True, quality=85)

        return f"/static/uploads/avatars/{file_name}", None
    except Exception as e:
        return None, str(e)