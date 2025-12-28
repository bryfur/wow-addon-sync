#!/usr/bin/env python3
"""Generate transparent icons from the original icon with white background."""

from PIL import Image, ImageEnhance
from pathlib import Path


def make_transparent(image, *, background=(255, 255, 255), alpha_power=1.0, alpha_floor=6):
    """Convert a solid white background to true transparency with clean anti-aliased edges.

    This does two things:
    1) Estimates alpha from how "non-white" a pixel is.
    2) Decontaminates edge colors by un-blending against the background color.

    That second step is what avoids the common "white halo" / jaggy edges.
    """
    img = image.convert("RGBA")
    bg_r, bg_g, bg_b = background

    out = Image.new("RGBA", img.size)
    src = img.load()
    dst = out.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b, _ = src[x, y]

            # For a white background, the amount of ink is captured well by 255 - min(channel).
            # This yields 0 for pure white, 255 for fully saturated/dark pixels.
            alpha_raw = 255 - min(r, g, b)
            if alpha_raw <= alpha_floor:
                dst[x, y] = (0, 0, 0, 0)
                continue

            a = (alpha_raw / 255.0) ** float(alpha_power)
            if a >= 0.999:
                dst[x, y] = (r, g, b, 255)
                continue

            # Un-blend (decontaminate) color against background:
            # C = a*F + (1-a)*B  =>  F = (C - (1-a)*B) / a
            inv_a = 1.0 / a
            nr = int(round((r - (1.0 - a) * bg_r) * inv_a))
            ng = int(round((g - (1.0 - a) * bg_g) * inv_a))
            nb = int(round((b - (1.0 - a) * bg_b) * inv_a))

            nr = 0 if nr < 0 else 255 if nr > 255 else nr
            ng = 0 if ng < 0 else 255 if ng > 255 else ng
            nb = 0 if nb < 0 else 255 if nb > 255 else nb

            dst[x, y] = (nr, ng, nb, int(round(a * 255)))

    return out


def brighten_rgb(image: Image.Image, factor: float) -> Image.Image:
    """Brighten RGB while preserving the alpha channel exactly."""
    img = image.convert("RGBA")
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Brightness(rgb).enhance(float(factor))
    r2, g2, b2 = rgb.split()
    return Image.merge("RGBA", (r2, g2, b2, a))

def main():
    icons_dir = Path("icons")
    original_path = icons_dir / "icon_original.png"
    
    if not original_path.exists():
        print(f"Error: {original_path} not found")
        return
    
    print(f"Loading {original_path}...")
    original = Image.open(original_path)
    original_size = original.size[0]  # Assuming square image
    
    print("Converting white background to transparent...")
    transparent_img = make_transparent(original)

    # Slight lift so the icon reads better in dark trays/themes.
    transparent_img = brighten_rgb(transparent_img, factor=1.10)
    
    # Save original size processed version first
    original_processed_path = icons_dir / "icon_processed.png"
    print(f"Saving original size processed icon ({original_size}x{original_size})...")
    transparent_img.save(original_processed_path, "PNG", optimize=True)
    print(f"  ✓ Saved {original_processed_path}")
    
    # Generate icons at different sizes
    sizes = [
        ("icon.png", 256),
        ("icon_256.png", 256),
        ("icon_128.png", 128),
        ("icon_64.png", 64),
        ("icon_48.png", 48),
        ("icon_32.png", 32),
        ("icon_16.png", 16),
    ]
    
    # Process in order from largest to smallest for ICO file
    icon_sizes_for_ico = {}
    for filename, size in sizes:
        output_path = icons_dir / filename
        print(f"Generating {filename} ({size}x{size})...")
        
        # Resize with high-quality resampling
        resized = transparent_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save as PNG with transparency
        resized.save(output_path, "PNG", optimize=True)
        print(f"  ✓ Saved {output_path}")
        
        # Collect images for ICO file (avoid duplicates)
        if size not in icon_sizes_for_ico:
            icon_sizes_for_ico[size] = resized
    
    # Generate ICO file for Windows (contains multiple resolutions)
    ico_path = icons_dir / "icon.ico"
    print(f"\nGenerating icon.ico with multiple resolutions...")
    # Sort by size (smallest to largest as Windows expects)
    sorted_sizes = sorted(icon_sizes_for_ico.keys())
    
    # For ICO files, we need to save with the sizes parameter
    # which tells Pillow to create an ICO with multiple embedded images
    if sorted_sizes:
        # Use the original transparent image and let Pillow resize to each size
        transparent_img.save(ico_path, format='ICO', 
                           sizes=[(s, s) for s in sorted_sizes])
        print(f"  ✓ Saved {ico_path} with {len(sorted_sizes)} resolutions: {sorted_sizes}")
    
    print("\nAll icons generated successfully!")

if __name__ == "__main__":
    main()
