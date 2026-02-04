import os
import random
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 直接读取云端环境变量 (兼容 Zeabur)
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
        if not data: return jsonify({"error": "No data"}), 400

        provider = data.get('provider', 'guest')
        mode = data.get('mode', 'txt2img')
        prompt = data.get('prompt', 'anime')
        image_base64 = data.get('image')
        user_key = data.get('api_key')

        print(f"收到请求: {provider} | {mode}")

        # ==========================================
        # 🎁 方案 A: 游客/保底模式 (Pollinations)
        # 不需要 Key，100% 能用，专门解决“画不出来”的问题
        # ==========================================
        if provider == 'guest':
            seed = random.randint(0, 1000000)
            # 优化提示词
            final_prompt = f"anime style, masterpiece, best quality, {prompt}"
            if mode == 'lineart': final_prompt = f"monochrome lineart, sketch, {prompt}"
            
            # 直接生成 URL
            image_url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&nologo=true&model=any-dark"
            return jsonify({"image_url": image_url})

        # ==========================================
        # ☁️ 方案 B: Google (Imagen/Gemini)
        # ==========================================
        elif provider == 'google':
            key = user_key if user_key else GOOGLE_API_KEY
            if not key: return jsonify({"error": "未配置 Google Key"}), 400

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            
            # 构建 Gemini 请求
            parts = [{"text": f"Draw anime style: {prompt}"}]
            if image_base64 and mode != 'txt2img':
                parts.append({"inlineData": {"mimeType": "image/png", "data": image_base64}})

            payload = {
                "contents": [{ "parts": parts }],
                # 移除 responseModalities 以兼容更多 Key 类型
            }
            
            resp = requests.post(url, json=payload, timeout=60)
            res_json = resp.json()
            
            if "error" in res_json:
                return jsonify({"error": f"Google 报错: {res_json['error']['message']}"}), 500

            # 尝试提取图片 (如果没有图片，说明该 Key 只能对话)
            try:
                content = res_json['candidates'][0]['content']['parts']
                for part in content:
                    if 'inlineData' in part:
                        return jsonify({"image_b64": part['inlineData']['data']})
                return jsonify({"error": "Google 仅返回了文本，该 Key 可能无绘图权限，请切换到游客模式。"}), 500
            except:
                return jsonify({"error": "解析 Google 数据失败"}), 500

        # ==========================================
        # 🤖 方案 C: OpenAI (DALL-E 3)
        # ==========================================
        elif provider == 'openai':
            key = user_key if user_key else OPENAI_API_KEY
            if not key: return jsonify({"error": "未配置 OpenAI Key"}), 400

            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                json={"model": "dall-e-3", "prompt": f"Anime style. {prompt}", "size": "1024x1024", "response_format": "b64_json"},
                timeout=60
            )
            res_json = resp.json()
            if "error" in res_json: return jsonify({"error": res_json['error']['message']}), 500
            return jsonify({"image_b64": res_json['data'][0]['b64_json']})

        return jsonify({"error": "未知引擎"}), 400

    except Exception as e:
        print(f"Crash: {e}")
        # 返回 JSON 错误而不是让服务器崩掉 (502)
        return jsonify({"error": f"后端处理出错: {str(e)}"}), 500

if __name__ == '__main__':
    # 强制监听 0.0.0.0 和 8080 端口 (Zeabur 标准)
    app.run(host='0.0.0.0', port=8080)
