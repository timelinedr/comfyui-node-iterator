import json
import requests
from typing import Any, Dict

def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_existing_inputs(workflow: Dict[str, Any], full_key: str) -> Dict[str, Any]:
    """Extract the current value of a nested input like 'Power Lora Loader (rgthree)/lora_1'."""
    if "/" not in full_key:
        return {}

    node_title, input_name = full_key.split("/", 1)

    for node in workflow.values():
        if isinstance(node, dict) and node.get("_meta", {}).get("title") == node_title:
            return node.get("inputs", {}).get(input_name, {})

    return {}


def update_workflow(workflow: Dict[str, Any], updates: Dict[str, Any]) -> None:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        title = node.get("_meta", {}).get("title")
        if not title:
            continue
        for full_key, value in updates.items():
            node_title, input_key = full_key.split("/", 1)
            if title == node_title:
                node.setdefault("inputs", {})
                node["inputs"][input_key] = value


def send_to_comfyui(prompt: Dict[str, Any], url: str) -> Dict[str, Any]:
    payload = {
        "prompt": prompt,
        "extra_pnginfo": {
            "workflow": json.dumps(prompt, separators=(",", ":"))
        }
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def build_label_string(values: Dict[str, Any], config: Dict[str, Any]) -> str:
    seen = set()
    parts = []

    # Output using config-specified labels first
    for key in config:
        label = config[key].get("label") or key.split("/")[-1]
        if label in values and label not in seen:
            val = values[label]
            # 👇 Check for resolution dicts and format nicely
            if isinstance(val, dict) and "width" in val and "height" in val:
                formatted = f"{val['width']}x{val['height']}"
                parts.append(f"{label}={formatted}")
            else:
                parts.append(f"{label}={val}")
            seen.add(label)

    # Then fill in any other label values not covered above
    for k, v in values.items():
        if k not in seen:
            parts.append(f"{k}={v}")

    return " / ".join(parts)


def set_save_image_prefix(workflow: Dict[str, Any], new_prefix: str) -> None:
    """Sets filename_prefix on any node that supports it."""
    for node in workflow.values():
        if isinstance(node, dict):
            inputs = node.setdefault("inputs", {})
            if "filename_prefix" in inputs:
                inputs["filename_prefix"] = new_prefix
            if "save_metadata" in inputs:
                inputs["save_metadata"] = True  # <-- force metadata save    


def xset_save_image_prefix(workflow: Dict[str, Any], new_prefix: str) -> None:
    """Finds all SaveImage nodes and sets their filename_prefix."""
    for node in workflow.values():
        if isinstance(node, dict) and node.get("class_type") == "SaveImage":
            node.setdefault("inputs", {})["filename_prefix"] = new_prefix

def sanitize_filename(label_str: str) -> str:
    """
    Convert a label string like 'steps=30 / cfg=6 / sampler=ddim / top=off'
    into a shell-safe filename like 'steps-30__cfg-6__sampler-ddim__top-off'
    """
    return label_str.replace(" / ", "__").replace("/", "_").replace("=", "-")

def append_prompt_keyword(workflow: Dict[str, Any], prompt_name: str, prompt_text: str) -> None:
    """Appends prompt_text to the 'text' input of a CLIPTextEncode node with a given title."""
    for node in workflow.values():
        if (
            isinstance(node, dict)
            and node.get("class_type") == "CLIPTextEncode"
            and node.get("_meta", {}).get("title") == prompt_name
        ):
            current_text = node.get("inputs", {}).get("text", "")
            if prompt_text not in current_text:
                node["inputs"]["text"] = current_text.rstrip() + "\n" + prompt_text

