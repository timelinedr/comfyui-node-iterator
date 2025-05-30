# comfyui-node-iterator
ComfyUI script tool to automate iteration on arbitrary nodes

This tool automates batch prompt submission to ComfyUI by modifying any exported workflow using a structured JSON config file.

## Files in this Repo

- `main.py` — Entry point for generating prompt variants and submitting them to ComfyUI.
- `helpers.py` — Utilities for modifying workflows and constructing filenames.
- `workflows/purple_bottle.json` — Sample ComfyUI API workflow file, to use your own export a known working workflow using the "Export (API)" option and save it in in the workflows folder (recommended)
- `configs/example.json` — Sample config demonstrating multi-variable iteration, you can make your own versions of this

## What It Does

Given a ComfyUI workflow and a config file, this tool:

- Iterates over combinations of input parameters (e.g. seed, cfg, LoRA strength).
- Applies changes to the workflow JSON in memory.
- Submits each modified workflow to ComfyUI via its REST API.
- Automatically skips duplicates by checking existing `.png` or `.mp4` files in the output folder, useful to restart sessions that crashed
- Saves metadata into generated `.png` files using `extra_pnginfo`.

## Running from the Command Line

From the project root, run:

python3 main.py ./workflows/purple_bottle.json ./configs/example.json

This starts with the workflow you export from ComfyUI as the base, then applies the iterations found in the config


## Constructing a Config File

Each key maps to a node input using the format:


"Node Title/Input Name"


Each entry must include:

- `values`: A list of values to iterate over.
- Optional: `label` — Controls how filenames are constructed.

Example:


{
  "KSampler/seed": {
    "label": "seed",
    "values": [2025, 2026]
  },
  "KSampler/cfg": {
    "label": "cfg",
    "values": [6, 12]
  },
  "Empty Latent Image/resolution": {
    "label": "res",
    "values": [
      { "width": 1024, "height": 1024 },
      { "width": 1280, "height": 720 }
    ]
  }
}


### Special Cases

- **LoRA Strengths**: You can include `"off"` in a list of strengths to skip loading a LoRA for that variant.
- **Resolution**: If `Empty Latent Image/resolution` is used, `width` and `height` will be set together as pairs (e.g. 1024×1024 and 1280×720, but *not* 1024×720).
- **LoRA Prompt Text**: You can optionally inject text into the positive or negative prompt based on LoRA state. Add this to your config under a strength entry:


"Power Lora Loader/lora_1/strength": {
    "label": "gball",
    "values": ["off", 0.5, 1.0, 1.5],
    "prompt_keyword": [
        {
        "prompt_name": "CLIP Text Encode (Prompt)",
        "prompt_text": "dishclothball"
        },
        {
        "prompt_name": "CLIP Text Encode (Negative Prompt)",
        "prompt_text": "hands"
        }
    ]
}


- **Metadata**: Saved into PNGs automatically.
- **Save Nodes**: All nodes with a `filename_prefix` input will be updated. If your workflow contains multiple save nodes (e.g. both image and video output), all will be affected by the same prefix.

## Output

Files are named based on the config labels and values, for example:

seed-2025__cfg-6__res-1280x720__gball-off__dart-1.5_00001_.png


Output is saved to location set here:

output_dir = "/workspace/ComfyUI/output"

If a `.png` or `.mp4` with the same prefix already exists, that variant will be skipped.
