from flask import Flask, render_template, request, jsonify
import re
import io
import os
import base64
import tempfile
from PIL import Image
import torch
from lavis.models import load_model_and_preprocess

app = Flask(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model, vis_processors, _ = load_model_and_preprocess(
    name="blip2_opt",
    model_type="cryoet-RW-DS ",
    is_eval=True,
    device=device,
)


def caption_image_from_path(image_path: str, num_captions: int = 5):
    raw_image = Image.open(image_path).convert("RGB")
    image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
    print(f"Processing image at: {image_path}")
    output = model.generate({"image": image}, num_captions=num_captions)
    cleaned_output = [re.sub(r"[^\x00-\x7F]+", "", text) for text in output]
    cleaned_output = [text.strip() for text in cleaned_output if text.strip()]
    if not cleaned_output:
        return ["Unknown."]
    return cleaned_output


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/caption", methods=["POST"])  # receives base64 dataURL
def caption():
    data = request.get_json(force=True)
    if not data or "image_data" not in data:
        return jsonify({"error": "No image_data provided."}), 400

    data_url: str = data["image_data"]
    try:
        header, b64data = data_url.split(",", 1)
    except ValueError:
        return jsonify({"error": "Malformed data URL."}), 400

    try:
        img_bytes = base64.b64decode(b64data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, format="PNG")
            tmp_path = tmp.name

        print("Processing image at:", tmp_path)
        captions = caption_image_from_path(tmp_path)
        print(f"Done generating captions: {captions}")
    except Exception as e:
        return jsonify({"error": f"Failed to process image: {e}"}), 500
    finally:
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

    return jsonify({"captions": captions})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
