import io, os
from PIL import Image, ImageDraw, ImageFont

W, H = 900, 480

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _circle_avatar(img_bytes: bytes | None, size: int, letter: str = "?") -> Image.Image:
    out  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    if img_bytes:
        try:
            photo = (
                Image.open(io.BytesIO(img_bytes))
                .convert("RGBA")
                .resize((size, size), Image.LANCZOS)
            )
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
            out.paste(photo, (0, 0), mask)
            return out
        except Exception:
            pass
    draw.ellipse([0, 0, size - 1, size - 1], fill="#1a2a3a")
    draw.text(
        (size // 2, size // 2),
        letter.upper(),
        font=_font(size // 3, bold=True),
        fill="#4a9eda",
        anchor="mm",
    )
    return out


def generate_card(
    mention: str,
    user_id: str,
    username: str,
    dc: str,
    is_premium: bool,
    estimated_date: str,
    color_name: str,
    color_hex: str,
    color_emoji: str,
    avatar_bytes: bytes | None,
) -> bytes:
    # ── background ──────────────────────────────────────────────────────────
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark rounded-rectangle card
    CARD_BG = "#181825"
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=22, fill=CARD_BG)

    # Subtle gradient: darker on left (avatar area) vs slightly lighter on right
    for x in range(0, 230):
        alpha = int(30 * (1 - x / 230))
        draw.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))

    # ── avatar ───────────────────────────────────────────────────────────────
    AV_R  = 68          # radius (diameter 136px — smaller than before)
    AV_CX = 140
    AV_CY = H // 2

    # Outer glow ring
    draw.ellipse(
        [AV_CX - AV_R - 10, AV_CY - AV_R - 10,
         AV_CX + AV_R + 10, AV_CY + AV_R + 10],
        outline="#1a3a5a", width=6,
    )
    # Main cyan ring
    draw.ellipse(
        [AV_CX - AV_R - 4, AV_CY - AV_R - 4,
         AV_CX + AV_R + 4, AV_CY + AV_R + 4],
        outline="#3a7aaa", width=3,
    )

    letter = (mention.lstrip("@") or "?")[0]
    av = _circle_avatar(avatar_bytes, AV_R * 2, letter=letter)
    img.paste(av, (AV_CX - AV_R, AV_CY - AV_R), av)

    # ── right panel ──────────────────────────────────────────────────────────
    draw = ImageDraw.Draw(img)          # re-bind after paste

    RX = 255            # right panel start x

    # Title
    draw.text(
        (RX, 32),
        "TELEGRAM PROFILE CARD",
        font=_font(30, bold=True),
        fill="#ffffff",
    )

    # Divider under title
    draw.line([(RX, 78), (W - 24, 78)], fill="#2e3e52", width=2)

    # ── fields ───────────────────────────────────────────────────────────────
    LABEL_COLOR = "#8899aa"
    WHITE       = "#e8f0f8"
    CYAN        = "#4ab8e8"

    fields = [
        ("Nama Lengkap",    mention,                           WHITE),
        ("User ID",         user_id,                          CYAN),
        ("Username",        username,                         CYAN),
        ("Data Center",     dc,                               WHITE),
        ("Akun Premium",    "Ya" if is_premium else "Tidak",  CYAN if is_premium else WHITE),
        ("Estimasi Dibuat", estimated_date,                   CYAN),
        ("Warna Profil",    color_name,                       color_hex),
    ]

    LX   = RX           # label x
    CLN  = RX + 188     # colon x
    VX   = RX + 208     # value x
    SY   = 96           # start y
    LH   = 52           # line height

    for i, (label, value, vcolor) in enumerate(fields):
        y = SY + i * LH
        draw.text((LX,   y), label,      font=_font(17, bold=True), fill=LABEL_COLOR)
        draw.text((CLN,  y), ":",        font=_font(17, bold=True), fill=LABEL_COLOR)
        draw.text((VX,   y), str(value), font=_font(17, bold=True), fill=vcolor)

    # Watermark
    draw.text(
        (W - 20, H - 14),
        "CekID Bot | @botallz",
        font=_font(10),
        fill="#2a3a4a",
        anchor="rm",
    )

    # ── export as PNG ────────────────────────────────────────────────────────
    out_rgb = Image.new("RGB", (W, H), CARD_BG)
    out_rgb.paste(img, (0, 0), img)

    buf = io.BytesIO()
    out_rgb.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()
