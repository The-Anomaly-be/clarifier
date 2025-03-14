from PIL import Image
import os
import math
from gradio_client import Client, handle_file
import time
import logging

# Import necessary libraries: PIL for image processing, os for file operations,
# math for calculations, gradio_client for API interactions, time for delays,
# and logging for logging events.

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('split_and_enhance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure logging to record events at INFO level and above,
# saving to 'split_and_enhance.log' and also printing to console.

def resize_to_nearest_1024(image):
    """Resize image so width and height are divisible by 1024 while maintaining aspect ratio."""
    original_width, original_height = image.size
    aspect_ratio = original_width / original_height

    # Calculate new width as the largest multiple of 1024 less than or equal to original width
    new_width = math.floor(original_width / 1024) * 1024
    if new_width == 0:
        new_width = 1024  # Ensure minimum width of 1024

    # Calculate new height based on aspect ratio
    new_height = round(new_width / aspect_ratio)
    # Make new height a multiple of 1024
    new_height = math.floor(new_height / 1024) * 1024
    if new_height == 0:
        new_height = 1024  # Ensure minimum height of 1024

    # Check if the new aspect ratio is close enough to the original
    if abs((new_width / new_height) - aspect_ratio) > 0.01:
        # If not, adjust width based on height
        new_width = round(new_height * aspect_ratio)
        new_width = math.floor(new_width / 1024) * 1024

    # Resize the image using LANCZOS filter for high-quality downscaling
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def split_image(image_path, output_dir):
    """Split image into 1024x1024 tiles and return list of tile paths."""
    try:
        # Open the source image
        img = Image.open(image_path)
    except Exception as e:
        # Log error if image cannot be opened
        logger.error(f"Error opening image: {e}")
        return []

    # Extract base name of the image file
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Resize the image to make dimensions multiples of 1024
    resized_img = resize_to_nearest_1024(img)
    width, height = resized_img.size
    # Calculate number of rows and columns of tiles
    rows = height // 1024
    cols = width // 1024

    # Log original and resized dimensions, and the grid size
    logger.info(f"Original size: {img.size}")
    logger.info(f"Resized to: {resized_img.size}")
    logger.info(f"Splitting into {rows} rows and {cols} columns")

    tile_paths = []
    for row in range(rows):
        for col in range(cols):
            # Calculate the coordinates for cropping the tile
            left = col * 1024
            top = row * 1024
            right = left + 1024
            bottom = top + 1024

            # Crop the tile from the resized image
            tile = resized_img.crop((left, top, right, bottom))
            # Generate filename for the tile
            output_filename = f"{base_name}R{row + 1}C{col + 1}.jpg"
            output_path = os.path.join(output_dir, output_filename)

            # Save the tile as JPEG with high quality
            tile.save(output_path, "JPEG", quality=95)
            tile_paths.append(output_path)
            logger.info(f"Saved {output_filename}")

    return tile_paths

def process_tiles(tile_paths, output_status_file="processing_status.txt"):
    """Process image tiles using the batch processing API with progress tracking."""
    try:
        # Connect to the Gradio API server running locally
        client = Client("http://127.0.0.1:7860/")
        logger.info("Connected to API server")
    except Exception as e:
        # Log error if connection fails
        logger.error(f"Failed to connect to API server: {e}")
        return

    if not tile_paths:
        # Warn if there are no tiles to process
        logger.warning("No tiles to process")
        return

    # Prepare the list of files for the API
    file_list = [handle_file(f) for f in tile_paths]
    total_tiles = len(file_list)

    # Define parameters for the batch processing API
    processing_params = {
        "files": file_list,
        "prompt": "universe, galaxies, planets and stars, masterpiece, best quality, highres, detailed, 4k",
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

        # Submit the batch processing job to the API
        job = client.submit(**processing_params, api_name="/batch_process_images")

        # Monitor the job's progress
        last_progress = -1
        while not job.done():
            status = job.status()
            if hasattr(status, 'progress_data') and status.progress_data:
                # Extract progress value (assuming it's a float between 0 and 1)
                progress = status.progress_data[0].get('value', 0) if status.progress_data else 0
                if isinstance(progress, (int, float)) and progress != last_progress:
                    # Calculate percentage and log it
                    percentage = min(100, max(0, int(progress * 100)))
                    logger.info(f"Processing progress: {percentage}%")
                    last_progress = progress
            time.sleep(1)  # Wait 1 second before checking again

        # Retrieve the final result once the job is done
        result = job.result()
        status, recent_enhancements, before_after = result

        # Save the processing status and results to a file
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

        # Open the output folder using the API
        client.predict(api_name="/open_output_folder")
        logger.info("Output folder opened")

    except Exception as e:
        # Log any errors that occur during processing
        logger.error(f"Error during processing: {e}")
        with open(output_status_file, 'w', encoding='utf-8') as f:
            f.write(f"Error: {str(e)}\n")

def splitandenhance(source_image, folder):
    """
    Split source image into tiles and enhance them using the API.

    Args:
        source_image (str): Path to the source image
        folder (str): Directory for tiles and output
    """
    # Log the start of the process
    logger.info(f"Starting process for {source_image}")

    # Split the image into tiles
    tile_paths = split_image(source_image, folder)

    if not tile_paths:
        # If no tiles were created, log an error and abort
        logger.error("Failed to split image, aborting")
        return

    # Process the tiles using the API
    process_tiles(tile_paths, os.path.join(folder, "processing_status.txt"))

    # Log the completion of the process
    logger.info("Process completed")

# Example usage
source = "soureceimage.jpg"
folder = "workfolder"
splitandenhance(source, folder)
