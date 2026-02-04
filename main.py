import os
import random
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        provider = data.get('provider', 'guest')
        mode = data.get('mode', 'txt2img')
        prompt = data.get('prompt', 'anime')
        image_base64 = data.get('image')
        
        # 优先使用前端传来的 Key
        user_key = data.get('api_key')

        # ==========================================
        # 🎁 模式 1: 游客/Guest (使用 Pollinations，无需 Key，绝对稳)
        # ==========================================
        if provider == 'guest':
            # Pollinations 是一个完全免费的公开接口，不需要 Key
            # 我们用它来作为“保底方案”，确保你的网站永远能画出图
            final_prompt = f"anime style, masterpiece, {prompt}"
            seed = random.randint(0, 100000)
            image_url = f"https://pollinations.ai/p/{final_prompt}?width=1024&height=1024&seed={seed}&nologo=true"
            return jsonify({"image_url": image_url})

        # ==========================================
        # ☁️ 模式 2: Google Gemini (需配置 Key)
        # ==========================================
        elif provider == 'google':
            key = user_key if user_key else GOOGLE_API_KEY
            if not key: return jsonify({"error": "未配置 Google API Key"}), 400
            
            # 使用 Imagen 3 (如果权限不足会自动报错) 或 Gemini Vision
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"Draw anime: {prompt}"},
                        *( [{"inlineData": {"mimeType": "image/png", "data": image_base64}}] if image_base64 else [] )
                    ]
                }],
                "generationConfig": { "responseModalities": ["IMAGE"] }
            }
            
            resp = requests.post(url, json=payload, timeout=60)
            res_json = resp.json()
            
            if "error" in res_json:
                return jsonify({"error": f"Google 报错: {res_json['error']['message']}"}), 500
                
            # 尝试提取图片
            try:
                b64 = res_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
                return jsonify({"image_b64": b64})
            except:
                return jsonify({"error": "Google 未返回图片，可能该 Key 无绘图权限。"}), 500

        # ==========================================
        # 🤖 模式 3: OpenAI (需配置 Key)
        # ==========================================
        elif provider == 'openai':
            key = user_key if user_key else OPENAI_API_KEY
            if not key: return jsonify({"error": "未配置 OpenAI API Key"}), 400

            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": f"Anime style, {prompt}",
                    "n": 1, "size": "1024x1024", "response_format": "b64_json"
                },
                timeout=60
            )
            res_json = resp.json()
            if "error" in res_json:
                return jsonify({"error": res_json['error']['message']}), 500
            return jsonify({"image_b64": res_json['data'][0]['b64_json']})

        return jsonify({"error": "未知引擎"}), 400

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
