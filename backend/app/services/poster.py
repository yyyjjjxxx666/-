"""海报图片生成：将AI生成的文案渲染到专业模板上，输出PNG。"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ..core.config import settings

# System Chinese fonts
_SYSTEM_FONTS = [
    "C:/Windows/Fonts/msyh.ttc",       # Microsoft YaHei
    "C:/Windows/Fonts/simhei.ttf",     # SimHei (黑体)
]
_SYSTEM_FONTS_FALLBACK = [
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Find a suitable Chinese font, falling back to default."""
    paths = _SYSTEM_FONTS + _SYSTEM_FONTS_FALLBACK
    if bold and os.path.exists("C:/Windows/Fonts/msyhbd.ttc"):
        paths.insert(0, "C:/Windows/Fonts/msyhbd.ttc")
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def generate_poster(content: dict, output_filename: str) -> str:
    """根据AI生成的文案内容生成专业海报。返回文件路径。"""
    os.makedirs(settings.POSTER_DIR, exist_ok=True)

    W, H = 800, 1200
    img = Image.new("RGB", (W, H), color="#0a1628")
    draw = ImageDraw.Draw(img)

    # ── Colours ──
    c_bg_dark = _hex_to_rgb("#0a1628")
    c_bg_mid = _hex_to_rgb("#132044")
    c_accent = _hex_to_rgb("#f0b90b")      # gold accent
    c_accent2 = _hex_to_rgb("#e8345e")     # warm red
    c_text_white = (255, 255, 255)
    c_text_muted = (170, 185, 210)
    c_card_bg = (20, 35, 70)

    # ── Gradient background ──
    for y in range(H):
        ratio = y / H
        r = int(c_bg_dark[0] + (c_bg_mid[0] - c_bg_dark[0]) * ratio)
        g = int(c_bg_dark[1] + (c_bg_mid[1] - c_bg_dark[1]) * ratio)
        b = int(c_bg_dark[2] + (c_bg_mid[2] - c_bg_dark[2]) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Top decorative bar ──
    draw.rectangle([(0, 0), (W, 8)], fill=c_accent)

    # ── Decorative circles (subtle) ──
    for cx, cy, r, opacity in [(680, 200, 180, 8), (100, 900, 120, 6), (700, 1050, 90, 5)]:
        overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, opacity))
        img = img.convert("RGBA")
        img.paste(overlay, (0, 0), overlay)
        img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Top accent line ──
    draw.rectangle([(40, 60), (120, 66)], fill=c_accent)

    # ── Category label ──
    category = content.get("category", "社团活动")
    font_cat = _find_font(18)
    draw.text((50, 80), f"✦  {category}", fill=c_accent, font=font_cat)

    # ── Headline ──
    headline = content.get("headline", "精彩活动")
    font_title = _find_font(46, bold=True)
    # Word wrap for long titles
    title_lines = _wrap_text(headline, font_title, W - 100)
    y = 130
    for line in title_lines:
        draw.text((50, y), line, fill=c_text_white, font=font_title)
        y += 58

    # ── Subtitle ──
    subtitle = content.get("subtitle", "")
    if subtitle:
        y += 10
        font_sub = _find_font(24)
        draw.text((50, y), subtitle, fill=c_text_muted, font=font_sub)
        y += 40

    y += 20

    # ── Divider ──
    draw.line([(50, y), (W - 50, y)], fill=c_accent, width=1)
    y += 30

    # ── Info section (date, time, location) ──
    info_items = []
    if content.get("date"):
        info_items.append(("📅", content["date"]))
    if content.get("time"):
        info_items.append(("⏰", content["time"]))
    if content.get("location"):
        info_items.append(("📍", content["location"]))

    font_info = _find_font(20)
    for icon, text in info_items:
        draw.text((60, y), f"{icon}  {text}", fill=c_text_muted, font=font_info)
        y += 36

    y += 30

    # ── Highlights ──
    highlights = content.get("highlights", [])
    if highlights:
        font_hl = _find_font(21)
        font_hl_title = _find_font(22, bold=True)
        draw.text((50, y), "🌟  活动亮点", fill=c_accent, font=font_hl_title)
        y += 42

        card_colors = [
            (c_accent2, (60, 35, 75)),
            ("#3b82f6", (25, 55, 90)),
            ("#10b981", (25, 70, 65)),
            ("#8b5cf6", (55, 40, 95)),
        ]
        for i, h in enumerate(highlights[:6]):
            color_key, card_bg = card_colors[i % len(card_colors)]
            cx1, cy1, cx2, cy2 = 50, y, W - 50, y + 68
            color_rgb = _hex_to_rgb(color_key) if isinstance(color_key, str) else color_key

            # Card background with rounded corners
            draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=10, fill=card_bg)
            # Left accent bar
            draw.rectangle([(cx1, cy1), (cx1 + 6, cy2)], fill=color_rgb)
            draw.text((cx1 + 22, cy1 + 16), h, fill=c_text_white, font=font_hl)
            y += 84

    y = max(y, 880)

    # ── CTA Button ──
    cta = content.get("cta", "立即报名")
    font_cta = _find_font(30, bold=True)
    btn_w, btn_h = 340, 70
    btn_x, btn_y = (W - btn_w) // 2, y + 30

    # Button shadow
    draw.rounded_rectangle([btn_x + 4, btn_y + 4, btn_x + btn_w + 4, btn_y + btn_h + 4],
                           radius=18, fill="#996d07")
    # Button body
    draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
                           radius=18, fill=c_accent)

    cta_bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0]
    cta_h = cta_bbox[3] - cta_bbox[1]
    draw.text((btn_x + (btn_w - cta_w) // 2, btn_y + (btn_h - cta_h) // 2 - 4),
              cta, fill="#0a1628", font=font_cta)

    # ── Footer ──
    font_footer = _find_font(16)
    footer_y = H - 80
    draw.line([(100, footer_y), (W - 100, footer_y)], fill=(40, 60, 100), width=1)
    footer_text = "社团管理与活动报名系统 · 扫码报名参与"
    bbox_f = draw.textbbox((0, 0), footer_text, font=font_footer)
    tw = bbox_f[2] - bbox_f[0]
    draw.text(((W - tw) // 2, footer_y + 16), footer_text, fill=(100, 120, 160), font=font_footer)

    # ── QR placeholder ──
    qr_box_y = footer_y - 120
    draw.rounded_rectangle([W - 150, qr_box_y, W - 50, qr_box_y + 100],
                           radius=6, outline=(60, 80, 120), width=1)
    draw.text((W - 142, qr_box_y + 38), "扫码\n签到", fill=(100, 120, 160), font=_find_font(14))

    # Save
    output_path = os.path.join(settings.POSTER_DIR, output_filename)
    img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)
    return output_path


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Simple word wrap for Chinese text (char-by-char)."""
    lines = []
    current = ""
    for ch in text:
        trial = current + ch
        bbox = font.getbbox(trial)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [text]
