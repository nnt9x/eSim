import os
from PIL import Image, ImageDraw, ImageFont
from unidecode import unidecode

def create_text_image(text, font_path=r'font\ArtySignature.otf', image_size=(300, 200), font_size=40):
    # Create a blank image with white background
    image = Image.new('RGB', image_size, 'white')
    draw = ImageDraw.Draw(image)

    # Get the absolute path to the font file
    font_path = os.path.join(os.path.dirname(__file__), font_path)
    font = ImageFont.truetype(font_path, font_size)

    # Remove diacritics from the text
    text = unidecode(text)

    # Calculate text size and position
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((image_size[0] - text_width) // 2, (image_size[1] - text_height) // 2)

    # Draw the text on the image
    draw.text(position, text, fill='black', font=font)

    # Save the image
    image_path = os.path.join(os.path.dirname(__file__), 'signature.png')
    image.save(image_path)

    # Return the image path
    return image_path
