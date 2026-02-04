import os
import random
import logging
import requests
from flask import Flask, render_template, request, jsonify

# 配置日志，方便在 Zeabur 控制台查看报错
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 从环境变量获取 API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        provider = data.get('provider', 'guest')
        mode = data.get('mode', 'txt2img')
        prompt = data.get('prompt', 'anime girl')
        image_base64 = data.get('image') # 用于图生图
        user_key = data.get('api_key')

        logger.info(f"收到请求: Provider={provider}, Mode={mode}, Prompt={prompt[:20]}...")

        # ==========================================
        # 🎁 方案 A: 游客模式 (Pollinations.ai)
        # ==========================================
        if provider == 'guest':
            seed = random.randint(0, 1000000)
            # 针对不同模式优化 Prompt
            base_prompt = f"anime style, masterpiece, best quality, {prompt}"
            if mode == 'lineart':
                base_prompt = f"monochrome lineart, sketch, black and white, {prompt}"
            elif mode == 'colorize':
                base_prompt = f"vibrant colors, coloring book style, {prompt}"

            # Pollinations 直接返回图片 URL，速度快且免费
            image_url = f"https://pollinations.ai/p/{base_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&nologo=true&model=any-dark"
            return jsonify({"image_url": image_url})

        # ==========================================
        # ☁️ 方案 B: Google Gemini
        # ==========================================
        elif provider == 'google':
            key = user_key if user_key else GOOGLE_API_KEY
            if not key:
                return jsonify({"error": "未配置 Google API Key，请在设置中输入"}), 400

            # 注意：Gemini 绘图模型通常是 imagen-3.0 或 gemini-pro-vision (但在 API 中通常只支持文本/多模态理解，绘图支持需确认模型版本)
            # 如果使用 Gemini 1.5 Flash，它主要生成文本。这里假设你使用的是支持绘图的 endpoint 或逻辑
            # 为了稳健性，这里演示标准的 generateContent 调用
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            
            headers = {'Content-Type': 'application/json'}
            # 构造提示词，强行要求描述画面，因为 Flash 模型本身不能直接画图，除非调用 Imagen 插件
            # *修正*：如果这是为了对接专门的绘画 API，请确保 URL 正确。
            # 这里我们保持你原有的逻辑，但增加错误捕获
            
            payload = {
                "contents": [{
                    "parts": [{"text": f"Draw this: {prompt}"}]
                }]
            }
            
            # 如果有图片上传（图生图）
            if image_base64 and mode != 'txt2img':
                payload['contents'][0]['parts'].append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": image_base64
                    }
                })

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            res_json = response.json()

            if "error" in res_json:
                logger.error(f"Google API Error: {res_json}")
                return jsonify({"error": res_json['error']['message']}), 500
            
            # 尝试解析返回内容 (注意：Flash 模型通常返回文本描述，而非直接图片Base64，除非是特定多模态输出)
            # 这里保留你的原有解析逻辑，但增加保护
            try:
                # 假设 API 返回了 inlineData (图片)
                candidates = res_json.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    for part in parts:
                        if 'inlineData' in part:
                            return jsonify({"image_b64": part['inlineData']['data']})
                
                # 如果没有图片，返回文本作为错误提示，或者回退
                return jsonify({"error": "Google 模型未返回图片数据，请检查模型权限或切换游客模式"}), 500
            except Exception as e:
                logger.error(f"Parsing Error: {str(e)}")
                return jsonify({"error": "解析 Google 返回数据失败"}), 500

        # ==========================================
        # 🤖 方案 C: OpenAI DALL-E 3
        # ==========================================
        elif provider == 'openai':
            key = user_key if user_key else OPENAI_API_KEY
            if not key:
                return jsonify({"error": "未配置 OpenAI Key"}), 400

            try:
                resp = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": f"Anime style, {prompt}",
                        "n": 1,
                        "size": "1024x1024",
                        "response_format": "b64_json"
                    },
                    timeout=60
                )
                res_json = resp.json()
                if "error" in res_json:
                    return jsonify({"error": res_json['error']['message']}), 500
                
                return jsonify({"image_b64": res_json['data'][0]['b64_json']})
            except Exception as e:
                return jsonify({"error": f"OpenAI 请求失败: {str(e)}"}), 500

        return jsonify({"error": "无效的服务商"}), 400

    except Exception as e:
        logger.error(f"Server Error: {str(e)}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    # 本地开发时使用，云端将由 Gunicorn 接管
    app.run(host='0.0.0.0', port=8080, debug=True)
