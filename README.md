# Clarifier
![Clarifier](https://theanomaly.be//images//clarifier.jpg)
# Advanced detail enhancement and upscaling using Clarity Refiners UI (runs locally)

This script I created for myself after using several "limited" paid services provides limitless upscaling with enhanced details for any picture, even the largest ones. It runs locally on a simple GPU. It splits the large image into 1024x1024 tiles and enhances them individually, then it recomposes the image. I'm using it to enhance further my 600 to 1000+ megapixels gigaprints (full wall printing, event banners, ...) based on my high resolution artworks.

## Installation of Pinokio with Clarity Refiners UI (the easiest way)

To use this script, you need to have the Clarity Refiners UI running locally. The easiest "one click" way is to use Pinokio for an automated install and configuration. Follow these steps to install it:

1. **Download Pinokio**: Visit [Pinokio's official website](https://pinokio.computer/) and download the installer for your operating system.
2. **Install Pinokio**: Run the installer and follow the on-screen instructions to complete the installation.
3. **Open Pinokio**: Launch the Pinokio application.
4. **Install Clarity Refiners UI**: Navigate to the "Components" section, search for "Clarity Refiners UI," and click "Install."
5. **Start the Component**: Once installed, start the Clarity Refiners UI component. This will launch the Gradio API server locally at `http://127.0.0.1:7860/`.

**Note**: Ensure the API server is running before executing the script.

## Prerequisites

Before running the script, ensure you have the following:

- **Python 3.6 or higher**: Install from [python.org](https://www.python.org/).
- **Required Python Libraries**:
  - `Pillow`: For image processing.
  - `gradio_client`: For interacting with the Gradio API.
  - `logging`: Included in Python’s standard library.

Install the required libraries using pip:

```bash
pip install Pillow gradio_client
```

---

## Usage

To use the script, follow these steps:

1. **Prepare Your Image**: Place your large image in a directory, e.g., `C:\enhance\sourceimage.jpg` (it also works on a Linux file system).
2. **Specify Output Folder**: Choose or create a folder where the tiles and processing status will be saved, e.g., `C:\enhance\workfolder`.
3. **Run the Script**: Open the script in a Python environment, set the `source`, `stylization` and `folder` variables, then execute:

```python
source = "C:\\enhance\\sourceimage.jpg"
stylization = "metallic paint, rust"
folder = "C:\\enhance\\workfolder"
splitandenhance(source, stylization, folder)
```

---

## Process Description

The script performs the following steps:

- **Resizing**:
  - The source image is resized slightly so its width and height are multiples of 1024 while preserving the aspect ratio.
  - It uses the LANCZOS resampling filter for high-quality resizing.

- **Splitting**:
  - The resized image is divided into 1024x1024 tiles.
  - Each tile is saved as a JPEG file in the specified folder with a naming convention like `imageR1C1.jpg` (R=Row, C=Column).

- **Enhancing**:
  - Tiles are sent to the Clarity Refiners UI API at `http://127.0.0.1:7860/` for enhancement.

- **Progress Monitoring**:
  - The script tracks the API’s batch processing progress, logging updates as percentages.

- **Collating the pieces into the output image**:
  - All the pieces are collated together to create the resulting image and save it as `originalname`_enhanced_full.jpg.
  - After processing, the status and enhancement details are saved to `processing_status.txt` in the output folder.
  - The API opens the output folder automatically upon completion.

---

## Parameter Descriptions

The enhancement process is governed by parameters that allow you to customize the output’s details, resolution, and quality. Adjust these in the code to tailor the results. Here’s a breakdown:

### `prompt`
### NEW: Stylization prompt influence is now added directly in the function call
- **Description**: A text string directing the enhancement toward specific themes or details (e.g., `"universe, galaxies, planets and stars, masterpiece, best quality, highres, detailed, 4k"` for space-themed, high-quality output).
- **Effect**: Shapes the content and style of added details.
- **Usage**: Modify to match your desired output (e.g., `"forest, trees, rivers, vibrant colors, highres"` for a natural landscape).
- **Tips**:
  - Use commas to separate ideas.
  - Include quality descriptors (e.g., "highres," "detailed").
  - Keep it concise but specific.

### `negative_prompt`
- **Description**: A text string listing qualities to avoid (e.g., `"worst quality, low quality, blurry, artifacts"`).
- **Effect**: Refines output by excluding specified flaws.
- **Usage**: Add terms like `"distorted, overexposed"` to prevent additional issues.
- **Tips**:
  - Be precise about unwanted traits.
  - Test additions incrementally.

### `seed`
- **Description**: Sets the random number generator’s starting point. `-1` randomizes it; a specific value (e.g., `42`) ensures consistency.
- **Effect**: Controls output reproducibility.
- **Usage**: Use `-1` for variety or a fixed number to replicate results.
- **Tips**:
  - Record successful seeds.
  - Use fixed seeds for coherence.

### `upscale_factor`
- **Description**: Defines resolution increase (e.g., `4` turns 1024x1024 tiles into 4096x4096).
- **Effect**: Higher values yield larger, detailed images but increase processing demands.
- **Usage**: Increase for sharper images or decrease (e.g., `2`) for faster results.
- **Tips**:
  - Start with `2` to test.
  - Watch memory limits with large factors.

### `controlnet_scale`
- **Description**: Sets ControlNet’s influence strength (e.g., `0.7` for moderate guidance).
- **Effect**: Higher values preserve the original layout; lower values allow creativity.
- **Usage**: Raise (e.g., `1.0`) for fidelity or lower (e.g., `0.3`) for artistic freedom.
- **Tips**:
  - Use higher values for subtle changes.
  - Experiment for balance.

### `controlnet_decay`
- **Description**: Controls how ControlNet’s influence fades (e.g., `1` for constant influence).
- **Effect**: Lower values (e.g., `0.9`) reduce guidance over time.
- **Usage**: Keep at `1` for consistency or lower for evolving enhancements.
- **Tips**:
  - Try `0.8`–`0.95` for gradual shifts.
  - Pair with `controlnet_scale`.

### `condition_scale`
- **Description**: Sets prompt influence strength (e.g., `7` for significant weight).
- **Effect**: Higher values align output with the prompt; lower values focus on the input image.
- **Usage**: Increase (e.g., `9`) for prompt-driven results or decrease (e.g., `3`) for subtlety.
- **Tips**:
  - Use `5`–`7` as a baseline.
  - Adjust per prompt dominance.

### `tile_width` and `tile_height`
- **Description**: Sets tile size (e.g., `512` and `512` for 512x480 patches).
- **Effect**: Smaller tiles reduce VRAM use but may affect coherence; larger tiles improve quality.
- **Usage**: Lower (e.g., `128`) for low-VRAM systems or raise (e.g., `512`) if hardware permits.
- **Tips**:
  - `512` uses most memory of an RTX 4080 with 16GB VRAM.
  - Test various settings with your own GPU.

### `denoise_strength`
- **Description**: Controls noise removal (e.g., `0.3` for moderate denoising).
- **Effect**: Higher values (e.g., `0.5`) sharpen details but risk artifacts; lower values (e.g., `0.1`) retain texture.
- **Usage**: Increase for clarity or decrease to preserve noise.
- **Tips**:
  - Experiment between `0.1` and `0.5`.
  - Check for artifacts.

### `num_inference_steps`
- **Description**: Sets processing steps (e.g., `100` for quality focus).
- **Effect**: More steps enhance detail but slow processing; fewer steps speed it up.
- **Usage**: Lower (e.g., `30`) for tests or raise (e.g., `150`) for high quality.
- **Tips**:
  - Use `50`–`100` practically.
  - Balance with time.

### `solver`
- **Description**: Chooses the algorithm (e.g., `"DPMSolver"` or `"DDIM"`).
- **Effect**: `"DPMSolver"` may be faster; `"DDIM"` offers different quality.
- **Usage**: Test both to compare.
- **Tips**:
  - `"DPMSolver"` is a solid default.
  - Experiment per image.

---

## Logging

The script logs events to:
- The console for real-time feedback.
- A file named `split_and_enhance.log` in the current working directory for records.

Logs include image sizes, tile counts, progress percentages, and errors.

**Error Handling**: Check the log file if issues occur.

## Example
This example used this settings:

    processing_params = {
        "files": file_list,
        "prompt": stylization + ", masterpiece, best quality, highres, detailed, 4k",
        "negative_prompt": "worst quality, low quality, blurry, artifacts",
        "seed": -1,
        "reuse_seed": False,
        "upscale_factor": 4,
        "controlnet_scale": 0.5,
        "controlnet_decay": 0.8,
        "condition_scale": 8,
        "tile_width": 512,
        "tile_height": 512,
        "denoise_strength": 0.4,
        "num_inference_steps": 100,
        "solver": "DDIM"
    }

I used "brushed metal, ceramic, rgb lighting" for the stylization. It got some artifacts in the seams, controlnet scale should have been higher for that to be fixed.

