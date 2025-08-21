import argparse
import json
import os
import re
import torch
from PIL import Image
from lavis.models import load_model_and_preprocess
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def evaluate_image(model, vis_processors, image_path):
    raw_image = Image.open(image_path).convert("RGB")
    image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
    output = model.generate({"image": image}, num_captions=5)
    cleaned_output = [re.sub(r'[^\x00-\x7F]+', '', text) for text in output]
    cleaned_output = [text.strip() for text in cleaned_output if text.strip()]
    if not cleaned_output:
        return ["Unknown."]
    return cleaned_output


def main():
    argparser = argparse.ArgumentParser(description="Evaluate an image using a pre-trained model.")
    argparser.add_argument("--image-json", nargs="+", type=str, required=True, help="Path to the JSON file containing image paths.")
    argparser.add_argument("--output-folder-prefix", type=str, required=True, help="Prefix for the output folder.")
    argparser.add_argument("--model-name", type=str, default="blip2_opt", help="Name of the pre-trained model to use.")
    argparser.add_argument("--model-type", type=str, default="cryoet-RW-DS", help="Type of the model to use.")
    args = argparser.parse_args()
    model, vis_processors, _ = load_model_and_preprocess(name=args.model_name, model_type=args.model_type, is_eval=True, device=device)

    for image_json in args.image_json:
        output_file = os.path.basename(image_json).replace(".json", "_output_full.tsv")
        print(f"Processing {image_json} and saving output to {output_file}")

        image_entries = []
        with open(image_json, "r") as f:
            data = json.load(f)
            image_entries.extend([(f"{args.output_folder_prefix}/{entry['image']}", entry["caption"]) for entry in data])

        with open(output_file, "w") as f:
            for image_path, caption in image_entries:
                if not os.path.exists(image_path):
                    print(f"Image path {image_path} does not exist. Skipping.")
                    continue
                all_outputs = evaluate_image(model, vis_processors, image_path)
                print(f"{image_path}:\n\tGround Truth: {caption}\n\tModel Output: {all_outputs[0]}; All Outputs: {all_outputs}")
                f.write(f"{image_path}\t{caption}\t{all_outputs[0]}\t{all_outputs}\n")
                f.flush()


if __name__ == "__main__":
    main()