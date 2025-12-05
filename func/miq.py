from PIL import Image, ImageDraw, ImageFont
import io
import textwarp

def create_quote_image(icon: io.BytesIO, content:str, author:str, color:bool = None) -> io.BytesIO:
    width, height = 800, 400

    img = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    icon = Image.open(icon)

    if not color:
        icon = icon.convert("L").convert("RGB")
    else:
        icon = icon.convert("RGB")

    icon_ratio = icon.width / icon.height
    new_height = height
    new_width = int(new_height * icon_ratio)
    resized_icon = icon.resize((new_width, new_height))

    icon_canvas = Image.new("RGB", (height, height), color=(255, 255, 255))
    offset_x = (height - new_width) // 2 if new_width < height else 0
    offset_y = (height - new_height) // 2 if new_height < height else 0
    icon_canvas.paste(resized_icon, (offset_x, offset_y))

    img.paste(icon_canvas, (0, 0))

    grad_width = 200
    gradient = Image.new("L", (grad_width, height), color=0)
    for x in range(grad_width):
        alpha = int(255 * (x / grad_width))
        for y in range(height):
            gradient.putpixel((x,y), alpha)
    black_area = Image.new("RGB", (grad_width, height), color=(0, 0, 0))
    img.paste(black_area, (height, 0), mask=gradient)

    font_quote = ImageFont.truetype("font/miq_n.ttf", 30)
    font_author = ImageFont.truetype("font/miq_n.ttf", 20)
    font_signature = ImageFont.truetype("font/miq_s.ttf", 20)

    max_width_quote = 20
    wrapped_quote = textwarp.fill(content, width=max_width_quote)
    bbox_quote = draw.multiline_textbbox((0, 0), content, font=font_quote)
    text_w_q = bbox_quote[2] - bbox_quote[0]
    text_h_q = bbox_quote[3] - bbox_quote[1]
    pos_quote = (
        height + (width - height -text_w_q) // 2,
        (height - text_h_q) //2 - 20
    )
    draw.multiline_text(pos_quote, wrapped_quote, font=font_quote, fill=(255, 255, 255))

    max_width_author = 20
    wrapped_author = textwarp.fill(author, width=max_width_author)
    bbox_author = draw.textbbox((0, 0), wrapped_author, font=font_author)
    text_w_a = bbox_author[2] - bbox_author[0]
    text_h_a = bbox_author[3] - bbox_author[1]
    pos_author = (
        height + (width - height - text_w_a)//2,
        pos_quote[1] + text_h_q + 10
    )
    draw.text(pos_author, wrapped_author, font=font_author, fill=(200, 200, 200))

    signature = "NyaXBot@1340"
    bbox_sig = draw.textbbox((0, 0), signature, font=font_signature)
    sig_w = bbox_sig[2] - bbox_sig[0]
    sig_h = bbox_sig[3] - bbox_sig[1]
    pos_sig = (
        width - sig_w - 10,
        height - sig_h -10
    )
    draw.text(pos_sig, signature, font=font_signature, fill=(150, 150, 150))

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    output.seek(0)

    return output
