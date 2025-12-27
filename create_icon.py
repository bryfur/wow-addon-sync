#!/usr/bin/env python3
"""
Create application icon
"""
from PIL import Image, ImageDraw, ImageFont

# Create a 256x256 icon
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background circle (dark blue)
margin = 20
draw.ellipse([margin, margin, size-margin, size-margin], 
             fill=(30, 60, 114, 255), outline=(100, 149, 237, 255), width=8)

# Draw sync arrows (circular arrows)
# Draw "W" for WoW in the center
try:
    # Try to use a larger font
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
except:
    font = ImageFont.load_default()

# Draw "W" in gold/yellow
text = "W"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
text_x = (size - text_width) // 2
text_y = (size - text_height) // 2 - 10

draw.text((text_x, text_y), text, fill=(255, 209, 0, 255), font=font)

# Draw small sync arrows in corners
arrow_color = (100, 200, 255, 255)
# Top right arrow (clockwise)
draw.arc([size-80, 30, size-30, 80], start=0, end=270, fill=arrow_color, width=6)
draw.polygon([(size-50, 35), (size-40, 30), (size-50, 25)], fill=arrow_color)

# Bottom left arrow (counter-clockwise) 
draw.arc([30, size-80, 80, size-30], start=180, end=90, fill=arrow_color, width=6)
draw.polygon([(50, size-35), (40, size-30), (50, size-25)], fill=arrow_color)

# Save as PNG
img.save('icon.png', 'PNG')
print("Icon created: icon.png")

# Create smaller versions for better scaling
for icon_size in [16, 32, 48, 64, 128, 256]:
    resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    resized.save(f'icon_{icon_size}.png', 'PNG')
    print(f"Created: icon_{icon_size}.png")
