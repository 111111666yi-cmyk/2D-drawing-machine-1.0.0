import os
import random
import requests
from flask import Flask, render_template, request, jsonify

# 初始化 Flask
app = Flask(__name__)

# 直接读取环境变量 (无需 load_dotenv)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        # 获取前端数据
        data = request.json
        if not data:
            return jsonify({"error": "没有接收到数据"}), 400

        provider = data.get('provider', 'guest')
        mode = data.get('mode', 'txt2img')
        prompt = data.get('prompt', 'anime')
        image_base64 = data.get('image')
        user_key = data.get('api_key')

        print(f"收到请求: {provider} | {mode}")

        # ==========================================
        # 🎁 游客模式 (Pollinations) - 100% 稳
        # ==========================================
        if provider == 'guest':
            # 这是一个完全公开的免费接口，不需要 Key，也不会报错
            seed = random.randint(0, 1000000)
            final_prompt = f"anime style, masterpiece, best quality, {prompt}"
            if mode == 'lineart': final_prompt = f"monochrome lineart, sketch, {prompt}"
            
            image_url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&nologo=true&model=any-dark"
            return jsonify({"image_url": image_url})

        # ==========================================
        # ☁️ Google 模式 (Imagen/Gemini)
        # ==========================================
        elif provider == 'google':
            key = user_key if user_key else GOOGLE_API_KEY
            if not key:
                return jsonify({"error": "未配置 Google Key"}), 400

            # 尝试使用 Gemini Pro Vision (目前免费且支持图生图)
            # 或者 Imagen (如果有权限)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            
            user_text = f"Draw anime: {prompt}"
            if mode == "lineart": user_text = "Convert to lineart"
            
            parts = [{"text": user_text}]
            if image_base64:
                parts.append({"inlineData": {"mimeType": "image/png", "data": image_base64}})

            payload = {
                "contents": [{ "parts": parts }],
                # 移除强制 IMAGE 模式，防止权限不足报错，改为通用生成
            }
            
            resp = requests.post(url, json=payload, timeout=60)
            res_json = resp.json()
            
            if "error" in res_json:
                return jsonify({"error": f"Google 报错: {res_json['error']['message']}"}), 500

            # 尝试提取
            try:
                # 查找图片数据
                content = res_json['candidates'][0]['content']['parts']
                for part in content:
                    if 'inlineData' in part:
                        return jsonify({"image_b64": part['inlineData']['data']})
                
                return jsonify({"error": "Google 仅返回了文本，该 Key 可能无绘图权限。"}), 500
            except:
                return jsonify({"error": "解析 Google 数据失败"}), 500

        # ==========================================
        # 🤖 OpenAI 模式
        # ==========================================
        elif provider == 'openai':
            key = user_key if user_key else OPENAI_API_KEY
            if not key: return jsonify({"error": "未配置 OpenAI Key"}), 400

            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": f"Anime style. {prompt}",
                    "size": "1024x1024",
                    "response_format": "b64_json"
                },
                timeout=60
            )
            res_json = resp.json()
            if "error" in res_json:
                return jsonify({"error": res_json['error']['message']}), 500
            return jsonify({"image_b64": res_json['data'][0]['b64_json']})

        return jsonify({"error": "未知引擎"}), 400

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    # 强制监听 0.0.0.0:8080，这是 Zeabur 的标准
    app.run(host='0.0.0.0', port=8080)
