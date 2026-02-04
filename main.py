import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# 加载服务器端的密钥 (绝对安全，因为用户接触不到这个文件)
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
        data = request.json
        provider = data.get('provider', 'server_google') # google / openai
        mode = data.get('mode', 'txt2img')
        prompt = data.get('prompt', 'anime')
        image_base64 = data.get('image')
        
        # === 密钥安全检查 ===
        # 逻辑：如果前端传了 user_key 就用用户的，否则用服务器的 SERVER_KEY
        user_key = data.get('api_key')
        
        final_key = ""
        if "google" in provider:
            final_key = user_key if user_key else SERVER_GOOGLE_KEY
            if not final_key: return jsonify({"error": "服务端未配置 Google 密钥，请联系站长或使用自定义 Key。"}), 400
        elif "openai" in provider:
            final_key = user_key if user_key else SERVER_OPENAI_KEY
            if not final_key: return jsonify({"error": "服务端未配置 OpenAI 密钥，请联系站长或使用自定义 Key。"}), 400

        # === 路由分发 ===
        
        # 🤖 引擎: OpenAI (DALL-E 3)
        if "openai" in provider:
            if mode != 'txt2img':
                return jsonify({"error": "OpenAI DALL-E 3 仅支持【灵感绘图】模式，不支持参考图。"}), 400

            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {final_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": f"Anime style, masterpiece. {prompt}",
                    "n": 1, "size": "1024x1024", "response_format": "b64_json"
                },
                timeout=60
            )
            res_json = resp.json()
            if "error" in res_json:
                return jsonify({"error": f"OpenAI 报错: {res_json['error']['message']}"}), 500
            
            return jsonify({"image": res_json['data'][0]['b64_json']})

        # ☁️ 引擎: Google (Imagen 3)
        elif "google" in provider:
            # Google 的绘图接口目前主要通过 Imagen 模型
            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={final_key}"
            
            # 构建提示词
            full_prompt = f"Anime style. {prompt}"
            if mode == 'lineart': full_prompt = f"Black and white anime line art sketch of {prompt}"
            if mode == 'colorize': full_prompt = f"Vibrant anime colors, coloring page style of {prompt}"
            
            payload = {
                "instances": [{ "prompt": full_prompt }],
                "parameters": { "sampleCount": 1 }
            }
            
            # 如果有图片，Google 免费接口(Imagen 3)目前暂不开放公网 img2img
            # 为了防止报错，我们做个拦截提示
            if mode != 'txt2img':
                return jsonify({"error": "Google 免费版暂不支持【垫图】功能，请切换到【灵感绘图】或等待官方开放权限。"}), 400

            resp = requests.post(url, json=payload, timeout=60)
            res_json = resp.json()
            
            if "error" in res_json:
                return jsonify({"error": f"Google 报错: {res_json['error']['message']}"}), 500
            
            if "predictions" in res_json:
                return jsonify({"image": res_json['predictions'][0]['bytesBase64Encoded']})
            else:
                return jsonify({"error": "生成成功但无图片，可能是敏感词拦截。"}), 500

        return jsonify({"error": "无效的引擎选择"}), 400

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
