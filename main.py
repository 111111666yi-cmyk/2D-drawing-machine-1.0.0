import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# 加载服务器端的“存货”密钥 (用于游客模式)
load_dotenv()
SERVER_GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
SERVER_OPENAI_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        # 1. 接收前端的指令
        data = request.json
        provider = data.get('provider', 'google') # google / openai
        mode = data.get('mode', 'txt2img')        # txt2img / lineart / colorize / redraw
        prompt = data.get('prompt', 'anime masterpiece')
        image_base64 = data.get('image')          # 垫图数据
        
        # 优先使用前端传来的 User Key，如果没有，则使用服务器环境变量的 Server Key
        user_key = data.get('api_key') 
        
        # ---------------------------------------------------------
        # 🤖 引擎 A: OpenAI (DALL-E 3)
        # ---------------------------------------------------------
        if provider == 'openai':
            api_key = user_key if user_key else SERVER_OPENAI_KEY
            if not api_key:
                return jsonify({"error": "未提供 OpenAI Key，且服务器未配置免费额度。"}), 400

            # DALL-E 3 暂不支持垫图 (img2img)，拦截报错
            if mode != 'txt2img':
                return jsonify({"error": "OpenAI DALL-E 3 暂不支持参考图功能，请使用灵感绘图模式。"}), 400

            headers = { "Content-Type": "application/json", "Authorization": f"Bearer {api_key}" }
            payload = {
                "model": "dall-e-3",
                "prompt": f"Anime style. {prompt}",
                "n": 1, 
                "size": "1024x1024",
                "response_format": "b64_json"
            }
            
            # 请求 OpenAI
            resp = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload, timeout=60)
            res_json = resp.json()
            
            if "error" in res_json:
                return jsonify({"error": f"OpenAI 报错: {res_json['error']['message']}"}), 500
            
            return jsonify({"image": res_json['data'][0]['b64_json']})

        # ---------------------------------------------------------
        # ☁️ 引擎 B: Google (Imagen 3 / Gemini)
        # ---------------------------------------------------------
        elif provider == 'google':
            api_key = user_key if user_key else SERVER_GOOGLE_KEY
            if not api_key:
                return jsonify({"error": "未提供 Google Key，且服务器未配置免费额度。"}), 400

            # 区分任务：画图用 Imagen，看图/修图用 Gemini
            if mode == 'txt2img':
                # === 文生图 (Imagen) ===
                url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={api_key}"
                payload = {
                    "instances": [{ "prompt": f"Anime style. {prompt}" }],
                    "parameters": { "sampleCount": 1 }
                }
                resp = requests.post(url, json=payload, timeout=60)
                res_json = resp.json()
                
                if "error" in res_json:
                    return jsonify({"error": f"Google Imagen 报错: {res_json['error']['message']}"}), 500
                
                if "predictions" in res_json:
                    return jsonify({"image": res_json['predictions'][0]['bytesBase64Encoded']})
                else:
                    return jsonify({"error": "Google 未返回图片，可能 Key 权限不足或 Prompt 违规。"}), 500
            
            else:
                # === 图生图/修图 (Gemini Vision) ===
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                # 构建指令
                task_instruction = ""
                if mode == 'lineart': task_instruction = "Extract the line art from this image. Black and white only."
                elif mode == 'colorize': task_instruction = f"Colorize this image. Style: {prompt}"
                elif mode == 'redraw': task_instruction = f"Redraw this image in anime style. {prompt}"

                payload = {
                    "contents": [{
                        "parts": [
                            { "text": task_instruction },
                            { "inlineData": { "mimeType": "image/png", "data": image_base64 } }
                        ]
                    }],
                    # 关键：告诉 Gemini 我要 json 或 text，这里我们尝试让它返回描述，
                    # 注意：Gemini 1.5 Flash 原生不支持直接返回‘编辑后的图片’，
                    # 真正的图生图需要 Imagen 3 的编辑接口（目前未完全开放）。
                    # 为了不报错，这里我们做一个“模拟返回”或者提示用户。
                }
                
                # 由于 Google API 限制，目前很难通过免费 API 做图生图
                # 这里返回一个友好的错误提示，引导用户使用文生图
                return jsonify({"error": "Google 免费版接口暂不支持【参考图编辑】功能，请切换到【灵感绘图】模式使用。"}), 400

        else:
            return jsonify({"error": "不支持的 AI 引擎"}), 400

    except Exception as e:
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
