from PIL import Image
import os
import math
from gradio_client import Client, handle_file
import time
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('split_and_enhance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def resize_to_nearest_1024(image):
    """Resize image so width and height are the smallest multiples of 1024 >= original size, maintaining aspect ratio."""
    original_width, original_height = image.size
    aspect_ratio = original_width / original_height

    # Calculate the smallest multiple of 1024 >= original width
    new_width = math.ceil(original_width / 1024) * 1024

    # Calculate corresponding height based on aspect ratio, then round to nearest multiple of 1024
    new_height = new_width / aspect_ratio
    new_height = math.ceil(new_height / 1024) * 1024

    # Check if the aspect ratio is preserved within a tolerance; adjust if needed
    adjusted_aspect_ratio = new_width / new_height
    if abs(adjusted_aspect_ratio - aspect_ratio) > 0.01:
        # Recalculate width based on height to better match original aspect ratio
        new_width = math.ceil((new_height * aspect_ratio) / 1024) * 1024

    logger.info(f"Resizing from {image.size} to ({new_width}, {new_height})")
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def split_image(image_path, output_dir):
    """Split image into 1024x1024 tiles and return list of tile paths."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        logger.error(f"Error opening image: {e}")
        return []

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    resized_img = resize_to_nearest_1024(img)
    width, height = resized_img.size
    rows = height // 1024
    cols = width // 1024

    logger.info(f"Original size: {img.size}")
    logger.info(f"Resized to: {resized_img.size}")
    logger.info(f"Splitting into {rows} rows and {cols} columns")

    tile_paths = []
    for row in range(rows):
        for col in range(cols):
            left = col * 1024
            top = row * 1024
            right = left + 1024
            bottom = top + 1024

            tile = resized_img.crop((left, top, right, bottom))
            output_filename = f"{base_name}R{row + 1}C{col + 1}.jpg"
            output_path = os.path.join(output_dir, output_filename)

            tile.save(output_path, "JPEG", quality=95)
            tile_paths.append(output_path)
            logger.info(f"Saved {output_filename}")

    return tile_paths, rows, cols  # Return rows and cols for later use

def process_tiles(tile_paths, stylization="HQ", output_status_file="processing_status.txt"):
    """Process image tiles using the batch processing API with progress tracking."""
    try:
        client = Client("http://127.0.0.1:7860/")
        logger.info("Connected to API server")
    except Exception as e:
        logger.error(f"Failed to connect to API server: {e}")
        return []

    if not tile_paths:
        logger.warning("No tiles to process")
        return []

    file_list = [handle_file(f) for f in tile_paths]
    total_tiles = len(file_list)

    processing_params = {
        "files": file_list,
        "prompt": stylization + ", masterpiece, best quality, highres, detailed, 4k",
        "negative_prompt": "worst quality, low quality, blurry, artifacts",
        "seed": -1,
        "reuse_seed": False,
        "upscale_factor": 4,
        "controlnet_scale": 0.7,
        "controlnet_decay": 1,
        "condition_scale": 7,
        "tile_width": 256,
        "tile_height": 256,
        "denoise_strength": 0.3,
        "num_inference_steps": 100,
        "solver": "DPMSolver"
    }

    try:
        logger.info("Starting batch processing...")
        job = client.submit(**processing_params, api_name="/batch_process_images")

        last_progress = -1
        while not job.done():
            status = job.status()
            if hasattr(status, 'progress_data') and status.progress_data:
                progress_unit = status.progress_data[0]
                if hasattr(progress_unit, 'progress'):  # Check for ProgressUnit with 'progress' attribute
                    progress = progress_unit.progress
                elif hasattr(progress_unit, 'value'):  # Fallback for older 'value' attribute
                    progress = progress_unit.value
                elif isinstance(progress_unit, dict):  # Fallback for dictionary structure
                    progress = progress_unit.get('value', 0)
                else:
                    logger.warning(f"Unknown progress_data structure: {progress_unit}")
                    progress = 0
                if isinstance(progress, (int, float)) and progress != last_progress:
                    percentage = min(100, max(0, int(progress * 100)))
                    logger.info(f"Processing progress: {percentage}%")
                    last_progress = progress
            time.sleep(1)  # Wait 1 second before checking again

        result = job.result()
        status, recent_enhancements, before_after = result

        with open(output_status_file, 'w', encoding='utf-8') as f:
            f.write(f"Processing Status: {status}\n\n")
            f.write("Recent Enhancements:\n")
            for enhancement in recent_enhancements:
                f.write(f"Image: {enhancement['image']}, Caption: {enhancement['caption']}\n")
            if before_after:
                f.write(f"\nBefore: {before_after[0]}\n")
                f.write(f"After: {before_after[1]}\n")

        logger.info(f"Processing completed. Status: {status}")
        logger.info(f"Processed {len(recent_enhancements)} images")
        logger.info(f"Status saved to {output_status_file}")

        client.predict(api_name="/open_output_folder")
        logger.info("Output folder opened")

        enhanced_paths = [enhancement['image'] for enhancement in recent_enhancements]
        return enhanced_paths

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        with open(output_status_file, 'w', encoding='utf-8') as f:
            f.write(f"Error: {str(e)}\n")
        return []

def collate_tiles(enhanced_paths, rows, cols, output_dir, base_name):
    """Collate enhanced tiles into a single image."""
    if not enhanced_paths:
        logger.error("No enhanced tiles to collate")
        return

    # Determine tile size from the first enhanced tile
    try:
        first_tile = Image.open(enhanced_paths[0])
        tile_size = first_tile.size[0]  # Assuming tiles are square (width = height)
        logger.info(f"Detected tile size: {tile_size}x{tile_size}")
    except Exception as e:
        logger.error(f"Error determining tile size from {enhanced_paths[0]}: {e}")
        tile_size = 4096  # Fallback to default if unable to determine
        logger.warning(f"Using fallback tile size: {tile_size}x{tile_size}")

    # Calculate full image dimensions
    full_width = cols * tile_size
    full_height = rows * tile_size

    # Create a new blank image to paste tiles into
    final_image = Image.new('RGB', (full_width, full_height))

    # Regex to extract row and column from filename
    pattern = re.compile(r'R(\d+)C(\d+)')

    for tile_path in enhanced_paths:
        try:
            # Extract row and column from the filename
            match = pattern.search(os.path.basename(tile_path))
            if not match:
                logger.warning(f"Could not parse row/column from {tile_path}")
                continue
            row = int(match.group(1)) - 1  # Convert to 0-based index
            col = int(match.group(2)) - 1

            # Open the enhanced tile
            tile = Image.open(tile_path)
            if tile.size[0] != tile_size or tile.size[1] != tile_size:
                tile = tile.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
                logger.info(f"Resized {os.path.basename(tile_path)} to {tile_size}x{tile_size}")

            # Calculate position to paste the tile
            left = col * tile_size
            top = row * tile_size

            # Paste the tile into the final image
            final_image.paste(tile, (left, top))
            logger.info(f"Pasted tile {os.path.basename(tile_path)} at ({left}, {top})")

        except Exception as e:
            logger.error(f"Error processing tile {tile_path}: {e}")

    # Save the final collated image
    final_output_path = os.path.join(output_dir, f"{base_name}_enhanced_full.jpg")
    final_image.save(final_output_path, "JPEG", quality=95)
    logger.info(f"Collated image saved to {final_output_path}")

def splitandenhance(source_image, folder, stylization):
    """Split source image into tiles, enhance them, and collate into a full image."""
    logger.info(f"Starting process for {source_image}")

    # Split the image into tiles and get grid dimensions
    tile_paths, rows, cols = split_image(source_image, folder)

    if not tile_paths:
        logger.error("Failed to split image, aborting")
        return

    # Process the tiles and get enhanced paths
    enhanced_paths = process_tiles(tile_paths, stylization, os.path.join(folder, "processing_status.txt"))

    if enhanced_paths:
        # Collate the enhanced tiles into a full image
        base_name = os.path.splitext(os.path.basename(source_image))[0]
        collate_tiles(enhanced_paths, rows, cols, folder, base_name)

    logger.info("Process completed")

# Example usage
source = "C:\\original.jpg"
folder = "C:\\workfolder"
stylization = "mechanical, gears, clockworks, metal, copper, silver, gold"
splitandenhance(source, folder, stylization)
