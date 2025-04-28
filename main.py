from flask import Flask, request, jsonify
import cv2
import base64
import os
import requests
import json
from flask_cors import CORS
from flask import Flask, request, jsonify

app = Flask(__name__)
CORS(app)

# === 1) Handle file upload and input parameters ===
@app.route('/generate_title', methods=['POST'])
def generate_title():
    # Check if file is part of the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Get parameters from request
    clickbait_choice = request.form.get('clickbait_choice', 'n').strip().lower()
    frame_no = int(request.form.get('frame_no', 0))

    # Save the uploaded video to a temporary path
    video_path = os.path.join("uploads", file.filename)
    file.save(video_path)

    # === 2) Extract frame ===
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify({"error": f"Cannot read frame {frame_no}"}), 400

    # === 3) Encode to base64 ===
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    b64 = base64.b64encode(buf).decode()
    data_url = f"data:image/jpeg;base64,{b64}"

    # === 4) Generate title prompt based on clickbait choice ===
    title_prompt = (
        "Generate a catchy, engaging YouTube title with some excitement—use words like 'incredible', 'amazing', 'you won’t believe'. "
        "Keep it under 15 words, specific to the game/app/place, without excessive hype."
    ) if clickbait_choice in ['y', 'yes'] else (
        "Generate a concise, engaging YouTube title specific to the game/app/place, under 15 words, without excessive hype."
    )

    # === 5) Build title payload ===
    title_payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": title_prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }]
    }

    # === 6) Send title request ===
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }
    tresp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=title_payload)

    if tresp.status_code >= 400:
        return jsonify({"error": "Title generation failed", "details": tresp.json()}), 400

    title_json = tresp.json()
    title = title_json["choices"][0]["message"]["content"].strip()

    return jsonify({"title": title})


if __name__ == "__main__":
    app.run(debug=True)
