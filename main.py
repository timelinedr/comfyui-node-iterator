import json
import copy
import itertools
import sys
import helpers
import os
import glob

def extract_config_groups(config):
    label_groups = {}
    no_label_items = {}

    for key, entry in config.items():
        label = entry.get("label")
        if label:
            label_groups.setdefault(label, {})[key] = entry["values"]
        else:
            no_label_items[key] = entry["values"]

    return label_groups, no_label_items

def expand_label_group(label, group, workflow):
    keys = list(group.keys())
    base_input = keys[0].rsplit("/", 1)[0]
    strength_key = f"{base_input}/strength"
    original_dict = helpers.extract_existing_inputs(workflow, base_input)

    variants = []

    # Special case: resolution pair iteration
    if len(group) == 1:
        only_key = list(group.keys())[0]
        if only_key.endswith("/resolution"):
            node_base = only_key.rsplit("/", 1)[0]
            for res in group[only_key]:
                variants.append({
                    f"{node_base}/width": res["width"],
                    f"{node_base}/height": res["height"]
                })
            return variants

    if strength_key in group:
        for strength in group[strength_key]:
            if strength == "off":
                variants.append({})
            else:
                variants.append({
                    base_input: {
                        "on": True,
                        "strength": strength,
                        "lora": original_dict.get("lora")
                    }
                })
    else:
        keys, values = zip(*group.items())
        for combo in itertools.product(*values):
            variants.append(dict(zip(keys, combo)))

    return variants

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 main.py <workflow_path> <config_path>")
        sys.exit(1)

    workflow_path = sys.argv[1]
    config_path = sys.argv[2]
    api_url = "http://127.0.0.1:4000/prompt"

    workflow = helpers.load_json(workflow_path)
    config = helpers.load_json(config_path)

    label_groups, no_label = extract_config_groups(config)

    expanded_by_label = {
        label: expand_label_group(label, group, workflow)
        for label, group in label_groups.items()
    }

    label_combo_sets = list(itertools.product(*expanded_by_label.values()))
    no_label_keys = list(no_label.keys())
    no_label_combos = list(itertools.product(*no_label.values())) if no_label else [()]

    seen_label_keys = set()

    for label_variant_group in label_combo_sets:
        merged_labeled = {}
        label_summary = {}

        for label, variant in zip(expanded_by_label.keys(), label_variant_group):
            if variant:
                merged_labeled.update(variant)
                for k, v in variant.items():
                    if isinstance(v, dict):
                        if "strength" in v:
                            label_summary[label] = v["strength"]
                    elif isinstance(v, (int, float, str)):
                        label_summary[label] = v
            else:
                label_summary[label] = "off"

        for ucombo in no_label_combos:
            merged = dict(merged_labeled)
            for k, v in zip(no_label_keys, ucombo):
                merged[k] = v
                label = config[k].get("label") or k.split("/")[-1]
                if isinstance(v, dict) and "width" in v and "height" in v:
                    label_summary[label] = f"{v['width']}x{v['height']}"
                else:
                    label_summary[label] = v

            # Patch for width/height
            for k in merged:
                if k.endswith("/width") or k.endswith("/height"):
                    base = k.rsplit("/", 1)[0]
                    width = merged.get(f"{base}/width")
                    height = merged.get(f"{base}/height")
                    if width and height:
                        for config_key, entry in config.items():
                            if config_key.endswith("/resolution") and entry.get("label"):
                                label_summary[entry["label"]] = f"{width}x{height}"

            label_key = tuple(sorted(label_summary.items()))
            if label_key in seen_label_keys:
                continue
            seen_label_keys.add(label_key)

            filename_label = helpers.build_label_string(label_summary, config)
            filename_prefix = helpers.sanitize_filename(filename_label)

            prompt = copy.deepcopy(workflow)
            helpers.update_workflow(prompt, merged)
            helpers.set_save_image_prefix(prompt, filename_prefix)

            for key, cfg_entry in config.items():
                if "/strength" in key and "prompt_keyword" in cfg_entry:
                    label = cfg_entry.get("label")
                    if label and label_summary.get(label) != "off":
                        keywords = cfg_entry["prompt_keyword"]
                        if isinstance(keywords, dict):
                            keywords = [keywords]
                        for kw in keywords:
                            helpers.append_prompt_keyword(prompt, kw["prompt_name"], kw["prompt_text"])

            output_dir = "/workspace/ComfyUI/output"
            found_existing = False

            for ext in ("*.png", "*.mp4"):
                glob_pattern = os.path.join(output_dir, f"{filename_prefix}{ext}")
                if glob.glob(glob_pattern):
                    found_existing = True
                    break

            if found_existing:
                print(f"Skipping (already exists): {filename_prefix}")
                continue

            print("Queued", filename_label)
            try:
                helpers.send_to_comfyui(prompt, api_url)
            except Exception as e:
                print(f"Error submitting prompt: {e}")

if __name__ == "__main__":
    main()
