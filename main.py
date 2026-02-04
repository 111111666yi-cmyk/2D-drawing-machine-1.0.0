import os
import requests
import time
import random
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()
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
        prompt = data.get('prompt', 'anime girl')
        
        # ==========================================
        # 🎁 引擎 1: Pollinations (真·免费 / 游客模式)
        # ==========================================
        if provider == 'guest':
            # 构建提示词
            final_prompt = f"anime style, masterpiece, best quality, {prompt}"
            if mode == 'lineart': final_prompt = f"monochrome lineart, sketch, white background, {prompt}"
            if mode == 'colorize': final_prompt = f"vibrant color, anime coloring, {prompt}"
            
            # 使用 Pollinations API (不需要 Key)
            seed = random.randint(0, 999999)
            image_url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?seed={seed}&width=1024&height=1024&nologo=true"
            
            # 验证图片是否生成 (Pollinations 返回的是流，我们稍微等待一下或直接返回 URL)
            # 为了前端能显示，我们直接返回这个 URL，前端 img src 设为这个 URL 即可
            return jsonify({"image_url": image_url})

        # ==========================================
        # 🤖 引擎 2: OpenAI (DALL-E 3)
        # ==========================================
        elif provider == 'openai':
            # 优先用前端传来的 Key，没有则用服务器的
            user_key = data.get('api_key')
            api_key = user_key if user_key else OPENAI_API_KEY
            
            if not api_key:
                return jsonify({"error": "未提供 OpenAI Key。"}), 400
            
            if mode != 'txt2img':
                return jsonify({"error": "DALL-E 3 暂不支持参考图重绘，请使用【灵感绘图】模式。"}), 400

            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json={
                    "model": "dall-e-3",
                    "prompt": f"Anime style. {prompt}",
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json"
                },
                timeout=60
            )
            res_json = resp.json()
            if "error" in res_json:
                return jsonify({"error": f"OpenAI 报错: {res_json['error']['message']}"}), 500
                
            return jsonify({"image_b64": res_json["data"][0]["b64_json"]})

        return jsonify({"error": "未知引擎"}), 400

    except Exception as e:
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
