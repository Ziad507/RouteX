"""
Utility functions for shipments app.

Includes:
- Image optimization and processing
- Custom helper functions for business logic
"""

from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os


def optimize_image(image_field, max_width=1200, max_height=1200, quality=85):
    """
    Optimize uploaded image for web use.
    
    Features:
    - Resize large images while maintaining aspect ratio
    - Convert to WebP for better compression
    - Reduce file size without significant quality loss
    
    Args:
        image_field: Django ImageField or InMemoryUploadedFile
        max_width: Maximum width in pixels (default 1200)
        max_height: Maximum height in pixels (default 1200)
        quality: Output quality 1-100 (default 85)
        
    Returns:
        Optimized InMemoryUploadedFile or None if optimization fails
    """
    if not image_field:
        return None
    
    try:
        # Open image
        img = Image.open(image_field)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize if needed
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save optimized image to BytesIO
        output = BytesIO()
        
        # Determine output format based on original
        original_ext = os.path.splitext(image_field.name)[1].lower()
        if original_ext in ['.jpg', '.jpeg']:
            img_format = 'JPEG'
            output_ext = '.jpg'
        elif original_ext == '.webp':
            img_format = 'WEBP'
            output_ext = '.webp'
        else:
            img_format = 'PNG'
            output_ext = '.png'
        
        img.save(output, format=img_format, quality=quality, optimize=True)
        output.seek(0)
        
        # Create new InMemoryUploadedFile
        base_name = os.path.splitext(os.path.basename(image_field.name))[0]
        optimized_name = f"{base_name}_optimized{output_ext}"
        
        return InMemoryUploadedFile(
            output,
            'ImageField',
            optimized_name,
            f'image/{img_format.lower()}',
            sys.getsizeof(output),
            None
        )
        
    except Exception as e:
        # Log error and return original image
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Image optimization failed: {str(e)}")
        return None

