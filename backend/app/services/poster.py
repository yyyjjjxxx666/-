"""海报图片生成：将AI生成的文案渲染到专业模板上，输出PNG。"""
import os
import sys
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ..core.config import settings


def _get_poster_abs_dir() -> str:
    """Return absolute poster output directory, matching the /static mount in main.py."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        # backend/app/services/poster.py → backend/app/services → backend/app → backend/
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, settings.POSTER_DIR)

# ── 8 套配色主题 ──
_COLOR_THEMES = [
    {
        "name": "深海蓝",
        "is_dark": True,
        "bg_dark": "#0a1628",
        "bg_mid": "#132044",
        "accent": "#f0b90b",
        "accent2": "#e8345e",
        "text_white": (255, 255, 255),
        "text_muted": (170, 185, 210),
        "card_bg": (20, 35, 70),
        "highlight_cards": ["#e8345e", "#3b82f6", "#10b981", "#8b5cf6"],
        "btn_shadow": "#996d07",
        "btn_text": "#0a1628",
    },
    {
        "name": "日落橙",
        "is_dark": True,
        "bg_dark": "#1a0f08",
        "bg_mid": "#2d1810",
        "accent": "#ff6b35",
        "accent2": "#ff8c42",
        "text_white": (255, 255, 255),
        "text_muted": (200, 180, 170),
        "card_bg": (45, 25, 20),
        "highlight_cards": ["#ff6b35", "#f7931e", "#ffc107", "#ff5722"],
        "btn_shadow": "#b3441e",
        "btn_text": "#1a0f08",
    },
    {
        "name": "森林绿",
        "is_dark": True,
        "bg_dark": "#0a1e14",
        "bg_mid": "#0f2d22",
        "accent": "#00c896",
        "accent2": "#7dd3a0",
        "text_white": (255, 255, 255),
        "text_muted": (160, 200, 180),
        "card_bg": (18, 45, 35),
        "highlight_cards": ["#00c896", "#34d399", "#059669", "#a3e635"],
        "btn_shadow": "#008055",
        "btn_text": "#0a1e14",
    },
    {
        "name": "紫夜",
        "is_dark": True,
        "bg_dark": "#170a2e",
        "bg_mid": "#251645",
        "accent": "#a855f7",
        "accent2": "#c084fc",
        "text_white": (255, 255, 255),
        "text_muted": (190, 175, 220),
        "card_bg": (35, 22, 65),
        "highlight_cards": ["#a855f7", "#8b5cf6", "#d946ef", "#6366f1"],
        "btn_shadow": "#5b2d8e",
        "btn_text": "#170a2e",
    },
    {
        "name": "极简白",
        "is_dark": False,
        "bg_dark": "#f8fafc",
        "bg_mid": "#e2e8f0",
        "accent": "#3b82f6",
        "accent2": "#2563eb",
        "text_white": (15, 23, 42),
        "text_muted": (100, 116, 139),
        "card_bg": (241, 245, 249),
        "highlight_cards": ["#3b82f6", "#6366f1", "#0ea5e9", "#8b5cf6"],
        "btn_shadow": "#1d4ed8",
        "btn_text": "#ffffff",
    },
    {
        "name": "霓虹粉",
        "is_dark": True,
        "bg_dark": "#1a0a16",
        "bg_mid": "#2d1028",
        "accent": "#ff2d95",
        "accent2": "#ff6b9d",
        "text_white": (255, 255, 255),
        "text_muted": (220, 175, 200),
        "card_bg": (45, 18, 40),
        "highlight_cards": ["#ff2d95", "#ff6b9d", "#f72585", "#b5179e"],
        "btn_shadow": "#a81d60",
        "btn_text": "#1a0a16",
    },
    {
        "name": "赛博青",
        "is_dark": True,
        "bg_dark": "#0a1a1c",
        "bg_mid": "#0f2c30",
        "accent": "#00e5ff",
        "accent2": "#18ffff",
        "text_white": (255, 255, 255),
        "text_muted": (150, 210, 215),
        "card_bg": (18, 44, 48),
        "highlight_cards": ["#00e5ff", "#00b8d4", "#18ffff", "#0097a7"],
        "btn_shadow": "#007c91",
        "btn_text": "#0a1a1c",
    },
    {
        "name": "复古暖",
        "is_dark": True,
        "bg_dark": "#1a1208",
        "bg_mid": "#2d1f10",
        "accent": "#d4a574",
        "accent2": "#f5e6c8",
        "text_white": (255, 255, 255),
        "text_muted": (210, 190, 165),
        "card_bg": (45, 32, 20),
        "highlight_cards": ["#d4a574", "#c9975a", "#b8860b", "#deb887"],
        "btn_shadow": "#8b6914",
        "btn_text": "#1a1208",
    },
]

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


def _hex_luminance(hex_str: str) -> float:
    """Relative luminance of a hex color (0-1 range). >0.5 = light background."""
    r, g, b = _hex_to_rgb(hex_str)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def generate_poster(content: dict, output_filename: str, design: dict = None) -> str:
    """根据AI生成的文案内容生成专业海报。优先使用LLM动态配色，否则随机选预设。返回文件路径。"""
    poster_dir = _get_poster_abs_dir()
    os.makedirs(poster_dir, exist_ok=True)

    # ── Resolve colours: LLM design > preset theme ──
    if design and all(k in design for k in ("bg_hex", "accent_hex", "accent2_hex")):
        # LLM-generated dynamic colours
        is_dark = _hex_luminance(design.get("bg_hex", "#0a1628")) < 0.5
        c_bg_dark = _hex_to_rgb(design["bg_hex"])
        c_bg_mid = _hex_to_rgb(design.get("bg_mid_hex", design["bg_hex"]))
        c_accent = _hex_to_rgb(design["accent_hex"])
        c_accent2 = _hex_to_rgb(design["accent2_hex"])
        c_text = (255, 255, 255) if is_dark else (15, 23, 42)
        c_text_muted = (170, 185, 210) if is_dark else (100, 116, 139)
        c_card_bg = tuple(int(c * 0.15) for c in _hex_to_rgb(design["bg_mid_hex"])) if is_dark else (241, 245, 249)
        c_btn_shadow = tuple(max(0, int(c * 0.65)) for c in c_accent)
        c_btn_text = (15, 23, 42) if _hex_luminance(design["accent_hex"]) > 0.5 else (255, 255, 255)
        # Highlight card colors: derive 4 variants from accent/accent2
        acc = c_accent
        acc2 = c_accent2
        highlight_cards = [
            design["accent2_hex"],
            design["accent_hex"],
            f"#{((acc[0] + 60) % 256):02x}{((acc[1] + 40) % 256):02x}{((acc[2] + 80) % 256):02x}",
            f"#{((acc2[0] + 80) % 256):02x}{((acc2[1] + 20) % 256):02x}{((acc2[2] + 60) % 256):02x}",
        ]
        grad_dir = design.get("gradient_dir", random.choice(["vertical", "diagonal"]))
        theme_name = design.get("theme_name", "AI定制")
    else:
        # Fallback to presets
        theme = random.choice(_COLOR_THEMES)
        is_dark = theme["is_dark"]
        c_bg_dark = _hex_to_rgb(theme["bg_dark"])
        c_bg_mid = _hex_to_rgb(theme["bg_mid"])
        c_accent = _hex_to_rgb(theme["accent"])
        c_accent2 = _hex_to_rgb(theme["accent2"])
        c_text = theme["text_white"]
        c_text_muted = theme["text_muted"]
        c_card_bg = theme["card_bg"]
        c_btn_shadow = _hex_to_rgb(theme["btn_shadow"])
        c_btn_text = _hex_to_rgb(theme["btn_text"])
        highlight_cards = theme["highlight_cards"]
        grad_dir = random.choice(["vertical", "diagonal"])
        theme_name = theme["name"]

    c_divider = c_text_muted if not is_dark else (40, 60, 100)
    c_qr_outline = c_text_muted if not is_dark else (60, 80, 120)
    c_footer_line = c_text_muted if not is_dark else (40, 60, 100)
    c_footer_text = c_text_muted

    W, H = 800, 1200
    img = Image.new("RGB", (W, H), color=c_bg_dark)
    draw = ImageDraw.Draw(img)

    # ── Gradient background ──
    for y in range(H):
        for x in range(0, W, 4):
            if grad_dir == "diagonal":
                ratio = (y / H + x / W) / 2
            else:
                ratio = y / H
            r = int(c_bg_dark[0] + (c_bg_mid[0] - c_bg_dark[0]) * ratio)
            g = int(c_bg_dark[1] + (c_bg_mid[1] - c_bg_dark[1]) * ratio)
            b = int(c_bg_dark[2] + (c_bg_mid[2] - c_bg_dark[2]) * ratio)
            draw.line([(x, y), (x + 3, y)], fill=(r, g, b))

    # ── Top decorative bar ──
    draw.rectangle([(0, 0), (W, 8)], fill=c_accent)

    # ── Decorative circles (subtle, with random offsets) ──
    base_circles = [(680, 200, 180, 8), (100, 900, 120, 6), (700, 1050, 90, 5)]
    for cx, cy, r, opacity in base_circles:
        cx += random.randint(-30, 30)
        cy += random.randint(-20, 20)
        r += random.randint(-15, 15)
        circle_color = (255, 255, 255, opacity) if is_dark else (0, 0, 0, max(2, opacity - 2))
        overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=circle_color)
        img = img.convert("RGBA")
        img.paste(overlay, (0, 0), overlay)
        img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Top accent line ──
    line_w = random.randint(60, 100)
    draw.rectangle([(40, 60), (40 + line_w, 66)], fill=c_accent)

    # ── Category label ──
    category = content.get("category", "社团活动")
    font_cat = _find_font(18)
    draw.text((50, 80), f"✦  {category}", fill=c_accent, font=font_cat)

    # ── Headline ──
    headline = content.get("headline", "精彩活动")
    font_title = _find_font(46, bold=True)
    title_lines = _wrap_text(headline, font_title, W - 100)
    y = 130
    for line in title_lines:
        draw.text((50, y), line, fill=c_text, font=font_title)
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

    # ── Highlights (3 layout variants) ──
    highlights = content.get("highlights", [])
    if highlights:
        font_hl = _find_font(21)
        font_hl_title = _find_font(22, bold=True)
        draw.text((50, y), "🌟  活动亮点", fill=c_accent, font=font_hl_title)
        y += 42

        layout_mode = random.randint(0, 2)
        hl_colors = highlight_cards

        if layout_mode == 0:
            # Single column — original style
            for i, h in enumerate(highlights[:6]):
                color_rgb = _hex_to_rgb(hl_colors[i % len(hl_colors)])
                cx1, cy1, cx2, cy2 = 50, y, W - 50, y + 68
                draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=10, fill=c_card_bg)
                draw.rectangle([(cx1, cy1), (cx1 + 6, cy2)], fill=color_rgb)
                draw.text((cx1 + 22, cy1 + 16), h, fill=c_text, font=font_hl)
                y += 84

        elif layout_mode == 1:
            # Two-column grid
            card_w = (W - 120) // 2
            for i, h in enumerate(highlights[:6]):
                color_rgb = _hex_to_rgb(hl_colors[i % len(hl_colors)])
                col = i % 2
                row = i // 2
                cx1 = 50 + col * (card_w + 20)
                cy1 = y + row * 74
                cx2 = cx1 + card_w
                cy2 = cy1 + 62
                draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=10, fill=c_card_bg)
                draw.rectangle([(cx1, cy1), (cx1 + 5, cy2)], fill=color_rgb)
                font_hl_sm = _find_font(18)
                draw.text((cx1 + 16, cy1 + 14), h, fill=c_text, font=font_hl_sm)
            y += ((min(len(highlights), 6) + 1) // 2) * 74

        else:
            # Compact rows — smaller, tighter cards
            for i, h in enumerate(highlights[:6]):
                color_rgb = _hex_to_rgb(hl_colors[i % len(hl_colors)])
                cx1, cy1, cx2, cy2 = 50, y, W - 50, y + 52
                draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=8, fill=c_card_bg)
                draw.rectangle([(cx1, cy1), (cx1 + 5, cy2)], fill=color_rgb)
                font_hl_sm = _find_font(19)
                draw.text((cx1 + 18, cy1 + 12), h, fill=c_text, font=font_hl_sm)
                y += 64

    y = max(y, 880)

    # ── CTA Button (random radius) ──
    cta = content.get("cta", "立即报名")
    font_cta = _find_font(30, bold=True)
    btn_w, btn_h = 340, 70
    btn_x, btn_y = (W - btn_w) // 2, y + 30
    btn_radius = random.choice([12, 18, 24, 35])

    draw.rounded_rectangle(
        [btn_x + 4, btn_y + 4, btn_x + btn_w + 4, btn_y + btn_h + 4],
        radius=btn_radius, fill=c_btn_shadow)
    draw.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
        radius=btn_radius, fill=c_accent)

    cta_bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0]
    cta_h = cta_bbox[3] - cta_bbox[1]
    draw.text((btn_x + (btn_w - cta_w) // 2, btn_y + (btn_h - cta_h) // 2 - 4),
              cta, fill=c_btn_text, font=font_cta)

    # ── Footer ──
    font_footer = _find_font(16)
    footer_y = H - 80
    draw.line([(100, footer_y), (W - 100, footer_y)], fill=c_footer_line, width=1)
    footer_text = "社团管理与活动报名系统 · 扫码报名参与"
    bbox_f = draw.textbbox((0, 0), footer_text, font=font_footer)
    tw = bbox_f[2] - bbox_f[0]
    draw.text(((W - tw) // 2, footer_y + 16), footer_text, fill=c_footer_text, font=font_footer)

    # ── QR placeholder ──
    qr_box_y = footer_y - 120
    draw.rounded_rectangle([W - 150, qr_box_y, W - 50, qr_box_y + 100],
                           radius=6, outline=c_qr_outline, width=1)
    draw.text((W - 142, qr_box_y + 38), "扫码\n签到", fill=c_footer_text, font=_find_font(14))

    # Save
    output_path = os.path.join(poster_dir, output_filename)
    img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)
    # Return URL-friendly relative path (matching /static mount in main.py)
    return os.path.join(settings.POSTER_DIR, output_filename).replace("\\", "/")


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
