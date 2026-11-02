#!/usr/bin/env python3
"""
Icon generator for JobFlow Desktop App
Creates .icns and .ico files with proper icon data
"""

import os
import sys
import subprocess
from pathlib import Path

def create_proper_icons():
    """Create proper icon files that PyInstaller can use."""
    assets_dir = Path(__file__).parent
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a proper icon with PIL - larger size for better quality
        img = Image.new('RGBA', (512, 512), (102, 126, 234, 255))  # Purple background
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fallback to default
        font_size = 200
        font_paths = [
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc", 
            "/Library/Fonts/Arial.ttf"
        ]
        
        font = None
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            except:
                continue
        
        if font is None:
            font = ImageFont.load_default()
        
        # Draw JF text centered
        text = "JF"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (512 - text_width) // 2
        y = (512 - text_height) // 2
        
        # Add text shadow for depth
        draw.text((x+3, y+3), text, fill=(0, 0, 0, 128), font=font)  # Shadow
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)  # Main text
        
        # Add a briefcase icon below the text
        briefcase_y = y + text_height + 20
        briefcase_size = 80
        briefcase_x = (512 - briefcase_size) // 2
        
        # Draw briefcase shape
        draw.rectangle([briefcase_x, briefcase_y, briefcase_x + briefcase_size, briefcase_y + briefcase_size//2], 
                      fill=(255, 255, 255, 200), outline=(255, 255, 255, 255), width=3)
        # Handle
        handle_y = briefcase_y - 10
        draw.rectangle([briefcase_x + 20, handle_y, briefcase_x + briefcase_size - 20, briefcase_y], 
                      outline=(255, 255, 255, 255), width=3)
        
        # Save high-quality PNG first
        png_file = assets_dir / "icon.png"
        img.save(png_file, format='PNG')
        
        # Create ICO with multiple sizes
        ico_file = assets_dir / "icon.ico"
        img.save(ico_file, format='ICO', sizes=[(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)])
        
        # Create ICNS using macOS iconutil if available
        icns_file = assets_dir / "icon.icns"
        iconset_dir = assets_dir / "icon.iconset"
        
        # Create iconset directory
        if iconset_dir.exists():
            import shutil
            shutil.rmtree(iconset_dir)
        iconset_dir.mkdir()
        
        # Generate all required icon sizes for ICNS
        sizes = [16, 32, 64, 128, 256, 512]
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(iconset_dir / f"icon_{size}x{size}.png", format='PNG')
            if size <= 256:  # Also create @2x versions for smaller sizes
                resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                resized_2x.save(iconset_dir / f"icon_{size}x{size}@2x.png", format='PNG')
        
        # Try to use iconutil to create ICNS
        try:
            result = subprocess.run(['iconutil', '-c', 'icns', str(iconset_dir), '-o', str(icns_file)], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Created ICNS with iconutil")
            else:
                raise Exception(f"iconutil failed: {result.stderr}")
        except Exception as e:
            print(f"⚠️  iconutil not available ({e}), creating simple ICNS")
            # Fallback: save 256x256 PNG as ICNS (not ideal but works)
            resized_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
            resized_256.save(icns_file, format='PNG')  # Some systems accept PNG as ICNS
        
        # Clean up iconset directory
        if iconset_dir.exists():
            import shutil
            shutil.rmtree(iconset_dir)
        
        print(f"✅ Created proper icon files:")
        print(f"   📄 {ico_file} ({os.path.getsize(ico_file)} bytes)")
        print(f"   📄 {icns_file} ({os.path.getsize(icns_file)} bytes)")
        print(f"   📄 {png_file} ({os.path.getsize(png_file)} bytes)")
        
    except ImportError as e:
        print(f"❌ Pillow not available: {e}")
        print("Please install Pillow: pip install Pillow")
        sys.exit(1)

if __name__ == "__main__":
    create_proper_icons()