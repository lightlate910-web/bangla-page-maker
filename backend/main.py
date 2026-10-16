from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from PIL import Image, ImageDraw, ImageFont

APP_DIR = Path(__file__).resolve().parent
FONT_DIR = APP_DIR / "fonts"

app = FastAPI(title="Bangla Page Maker API", version="1.0.0")

# Set FRONTEND_ORIGIN in Render, e.g. https://your-site.netlify.app
origins_env = os.getenv("FRONTEND_ORIGIN", "*")
origins = [x.strip() for x in origins_env.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["X-Page-Count", "X-Filename"],
)

class GenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1_000_000)
    width: int = Field(default=240, ge=128, le=1000)
    height: int = Field(default=320, ge=160, le=2000)
    lines_per_page: int = Field(default=10, ge=4, le=40)
    font_size: int = Field(default=16, ge=8, le=64)
    quality: int = Field(default=65, ge=30, le=95)
    include_page_numbers: bool = True

    @field_validator("text")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("প্রথমে কিছু লেখা পেস্ট করো বা TXT ফাইল আপলোড করো।")
        return value

def get_font(size: int) -> ImageFont.FreeTypeFont:
    # Put a Unicode Bengali TTF font in backend/fonts/ for consistent production rendering.
    env_font = os.getenv("BENGALI_FONT")
    candidates = [
        Path(env_font) if env_font else None,
        FONT_DIR / "NotoSansBengali-Regular.ttf",
        FONT_DIR / "NotoSerifBengali-Regular.ttf",
        Path("/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSerifBengali-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/Nirmala.ttf"),
        Path("C:/Windows/Fonts/Vrinda.ttf"),
    ]
    for path in candidates:
        if path and path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                pass
    raise HTTPException(
        status_code=500,
        detail="বাংলা ফন্ট পাওয়া যায়নি। backend/fonts/ ফোল্ডারে NotoSansBengali-Regular.ttf যোগ করো।",
    )

def wrap_text(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    # Preserve paragraph breaks while wrapping by measured pixel width.
    lines: list[str] = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        words = re.findall(r"\S+", paragraph)
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            box = draw.textbbox((0, 0), candidate, font=font, direction="ltr")
            if box[2] - box[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                # A single unusually long token is kept intact.
                current = word
        if current:
            lines.append(current)
    return lines or [""]

def create_pages(req: GenerateRequest) -> list[bytes]:
    image_probe = Image.new("RGB", (req.width, req.height), "white")
    probe_draw = ImageDraw.Draw(image_probe)
    font_size = req.font_size
    margin = max(6, round(req.width * 0.035))
    title_h = 20 if req.include_page_numbers else 8
    while font_size >= 8:
        font = get_font(font_size)
        bbox = probe_draw.textbbox((0, 0), "বাংলা পরীক্ষা", font=font)
        line_height = max(font_size + 4, bbox[3] - bbox[1] + 5)
        available = req.height - margin * 2 - title_h
        if line_height * req.lines_per_page <= available:
            break
        font_size -= 1
    if font_size < 8:
        raise HTTPException(status_code=422, detail="এই ছবির মাপে এত লাইন রাখা যাচ্ছে না। উচ্চতা বাড়াও বা লাইনের সংখ্যা কমাও।")
    font = get_font(font_size)
    lines = wrap_text(req.text, probe_draw, font, req.width - margin * 2)
    pages = [lines[i:i + req.lines_per_page] for i in range(0, len(lines), req.lines_per_page)]
    page_bytes: list[bytes] = []
    for index, page_lines in enumerate(pages, start=1):
        image = Image.new("RGB", (req.width, req.height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        y = margin
        if req.include_page_numbers:
            draw.text((margin, y), f"{index:04d}", font=ImageFont.truetype(font.path, max(8, min(12, font_size))), fill=(95, 95, 95))
            y += title_h
            draw.line((margin, y - 3, req.width - margin, y - 3), fill=(205, 205, 205), width=1)
        y += 1
        for line in page_lines:
            draw.text((margin, y), line, font=font, fill=(20, 20, 20))
            y += line_height
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=req.quality, optimize=True, progressive=False)
        page_bytes.append(buf.getvalue())
    return page_bytes

@app.get("/")
def root():
    return {"name": "Bangla Page Maker API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/generate")
def generate(req: GenerateRequest):
    try:
        pages = create_pages(req)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ছবি তৈরি করতে সমস্যা হয়েছে: {str(exc)[:200]}") from exc

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, data in enumerate(pages, start=1):
            archive.writestr(f"{index:04d}.jpg", data)
    zip_buffer.seek(0)
    headers = {
        "Content-Disposition": 'attachment; filename="bangla-pages.zip"',
        "X-Page-Count": str(len(pages)),
        "X-Filename": "bangla-pages.zip",
        "Cache-Control": "no-store",
    }
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)
