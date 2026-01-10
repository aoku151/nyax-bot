from PIL import Image, ImageDraw, ImageFont
import io
from io import BytesIO
import textwrap
from func.log import get_log
import cairosvg
import re
import os

EMOJI_PATTERN = re.compile(r'_([a-zA-Z0-9\-]+)_')
emoji_dire = "nyax/emoji"

def adjust_font_size(draw, text: str, font_path: str, max_pixel_width: int, max_height: int, initial_size: int, min_size: int = 15, emoji_dir="nyax/emoji"): 
    size = initial_size 
    while size >= min_size: 
        font = ImageFont.truetype(font_path, size) 
        lines = wrap_text_by_pixel_with_emojis(draw, text, font, max_pixel_width, emoji_dir) 
        total_height = len(lines) * (font.size + 5) 
        if total_height <= max_height: 
            return lines, font 
        size -= 2 
    # 最小サイズでも収まらない場合 
    font = ImageFont.truetype(font_path, min_size) 
    lines = wrap_text_by_pixel_with_emojis(draw, text, font, max_pixel_width, emoji_dir) 
    return lines, font

def load_svg_as_png(path: str, target_h: int): 
    """ 
    SVG を読み込み PNG に変換し、高さ target_h にリサイズして返す 
    """ 
    if not os.path.exists(path): 
        return None 
    try: 
        # with で安全に close 
        with open(path, "rb") as f: 
            svg_bytes = f.read() 
        png_data = cairosvg.svg2png(bytestring=svg_bytes) 
        emoji_img = Image.open(BytesIO(png_data)).convert("RGBA") 
        # アスペクト比維持リサイズ 
        ow, oh = emoji_img.size 
        tw = int(ow * (target_h / oh)) 
        emoji_img = emoji_img.resize((tw, target_h), Image.LANCZOS) 
        return emoji_img 
    except Exception: 
        return None

def measure_line_width(draw, line: str, font, emoji_dir="nyax/emoji"): 
    tokens = EMOJI_PATTERN.split(line) 
    width = 0 
    for i, token in enumerate(tokens): 
        if i % 2 == 1: 
            # 絵文字 
            path = f"{emoji_dir}/{token}.svg" 
            emoji_img = load_svg_as_png(path, font.size) 
            if emoji_img: 
                width += emoji_img.size[0] 
            else: 
                width += draw.textlength(f"_{token}_", font=font) 
        else: 
            width += draw.textlength(token, font=font) 
    return width

def wrap_text_by_pixel_with_emojis(draw, text: str, font, max_pixel_width: int, emoji_dir="nyax/emoji"): 
    tokens = EMOJI_PATTERN.split(" ".join(text.splitlines())) 
    lines = [] 
    line_tokens = [] 
    line_width = 0 
    def token_width(tok, is_emoji): 
        # print(tok)
        if not is_emoji: 
            return draw.textlength(tok, font=font) 
        path = f"{emoji_dir}/{tok}.svg" 
        emoji_img = load_svg_as_png(path, font.size) 
        if emoji_img: 
            return emoji_img.size[0] 
        return draw.textlength(f"_{tok}_", font=font) 
    for i, tok in enumerate(tokens): 
        is_emoji = (i % 2 == 1) 
        if not is_emoji: 
            # 通常文字は1文字ずつ 
            for ch in tok: 
                w = draw.textlength(ch, font=font) 
                if line_width + w > max_pixel_width and line_tokens: 
                    lines.append("".join(line_tokens)) 
                    line_tokens = [] 
                    line_width = 0 
                line_tokens.append(ch) 
                line_width += w 
        else: 
            # 絵文字は分割しない 
            w = token_width(tok, True) 
            if line_width + w > max_pixel_width and line_tokens: 
                lines.append("".join(line_tokens)) 
                line_tokens = [] 
                line_width = 0 
            line_tokens.append(f"_{tok}_") 
            line_width += w 
        print(lines)
    if line_tokens: 
        lines.append("".join(line_tokens)) 
    return lines

def render_line_with_emojis(img, draw, line: str, font, area_left: int, area_right: int, y: int, emoji_dir="nyax/emoji", fill=(255,255,255)): 
    tokens = EMOJI_PATTERN.split(line) 
    # 行幅計算 
    line_width = measure_line_width(draw, line, font, emoji_dir) 
    area_width = area_right - area_left 
    x = int(area_left + (area_width - line_width) // 2) 
    print(tokens)
    # 描画 
    for i, token in enumerate(tokens): 
        print(i)
        print(token)
        if i % 2 == 1: 
            # 絵文字 
            path = f"{emoji_dir}/{token}.svg" 
            emoji_img = load_svg_as_png(path, font.size) 
            if emoji_img: 
                # 白背景 
                tw, th = emoji_img.size 
                bg = Image.new("RGB", (tw, th), (255, 255, 255)) 
                bg.paste(emoji_img, (0, 0), emoji_img) 
                img.paste(bg, (int(x), int(y))) 
                x += tw 
            else: 
                text = f"_{token}_" 
                draw.text((x, y), text, font=font, fill=fill) 
                x += draw.textlength(text, font=font) 
        else: 
            draw.text((x, y), token, font=font, fill=fill) 
            x += draw.textlength(token, font=font)
    

def draw_quote_with_emojis(img, draw, quote: str, font, area_left: int, area_right: int, area_height: int, start_y: int, emoji_dir="nyax/emoji", fill=(255,255,255)): 
    max_pixel_width = area_right - area_left - 40 
    lines = wrap_text_by_pixel_with_emojis(draw, quote, font, max_pixel_width, emoji_dir) 
    total_height = len(lines) * (font.size + 5) 
    y = int(start_y + (area_height - total_height) // 2) 
    print(lines)
    for line in lines: 
        render_line_with_emojis(img, draw, line, font, area_left, area_right, y, emoji_dir, fill) 
        y += font.size + 5

def draw_centered_multiline(draw, text_lines, font, area_left, area_right, start_y, fill, line_spacing=5):
    area_width = area_right - area_left
    y = start_y
    for line in text_lines:
        line_width = draw.textlength(line, font=font)
        x = area_left + (area_width - line_width) // 2
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_spacing

def create_quote_image(width:int, height:int, icon_bytes: BytesIO, quote: str, author: str, color: bool = False) -> BytesIO: 
    img = Image.new("RGB", (width, height), color=(0, 0, 0)) 
    draw = ImageDraw.Draw(img) 
    # --- アイコン --- 
    icon = Image.open(icon_bytes) 
    icon = icon.convert("RGB") if color else icon.convert("L").convert("RGB") 
    icon_ratio = icon.width / icon.height 
    new_height = height 
    new_width = int(new_height * icon_ratio) 
    resized_icon = icon.resize((new_width, new_height)) 
    icon_canvas = Image.new("RGB", (height, height), (255, 255, 255)) 
    offset_x = max(0, (height - new_width) // 2) 
    icon_canvas.paste(resized_icon, (offset_x, 0)) 
    img.paste(icon_canvas, (0, 0)) 
    # --- グラデーション --- 
    grad_width = 200 
    gradient = Image.new("L", (grad_width, height), 0) 
    for x in range(grad_width): 
        alpha = int(255 * (x / grad_width)) 
        for y in range(height): 
            gradient.putpixel((x, y), alpha) 
    black_area = Image.new("RGB", (grad_width, height), (0, 0, 0)) 
    img.paste(black_area, (height, 0), mask=gradient) 
    # --- フォント --- 
    font_path = "font/miq_n.ttf" 
    quote_lines, font_quote = adjust_font_size( draw, quote, font_path, max_pixel_width=width - height - 40, max_height=height // 2, initial_size=25, min_size=15 ) 
    author_lines, font_author = adjust_font_size( draw, author, font_path, max_pixel_width=width - height - 40, max_height=height // 4, initial_size=20, min_size=15 ) 
    # --- Quote 描画 --- 
    draw_quote_with_emojis(img, draw, quote, font_quote, height, width, height, 0) 
    # --- Author 描画 --- 
    total_author_height = len(author_lines) * (font_author.size + 5) 
    y = int((height - total_author_height) // 2 + height // 4) 
    for line in author_lines: 
        line_width = draw.textlength(line, font=font_author) 
        x = int(height + (width - height - line_width) // 2) 
        draw.text((x, y), line, font=font_author, fill=(200, 200, 200)) 
        y += font_author.size + 5 
    # --- 署名 --- 
    signature = "NyaXBot@1340" 
    font_sig = ImageFont.truetype(font_path, 20) 
    sig_w = draw.textlength(signature, font=font_sig) 
    sig_h = font_sig.size 
    draw.text((width - sig_w - 10, height - sig_h - 10), signature, font=font_sig, fill=(150, 150, 150)) 
    # --- 出力 --- 
    output = BytesIO() 
    img.save(output, format="JPEG", quality=85) 
    output.seek(0) 
    return output
