import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# 云端部署会自动读取环境变量中的 Key
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)

# 首页路由：负责把你的网页 index.html 显示出来
@app.route('/')
def index():
    return render_template('index.html')

# 核心接口：负责把提示词发给 Google AI 并拿回图片
@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    mode = data.get('mode', 'txt2img')
    prompt = data.get('prompt', '1girl, masterpiece')
    image_base64 = data.get('image')

    if not GOOGLE_API_KEY:
        return jsonify({"error": "云端未检测到 API KEY，请在 Zeabur 后台配置环境变量。"}), 400

    try:
        # 使用 Google Gemini 1.5 Flash 接口
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"High-quality anime illustration: {prompt}"},
                    *( [{"inlineData": {"mimeType": "image/png", "data": image_base64}}] if image_base64 else [] )
                ]
            }],
            "generationConfig": { "responseModalities": ["IMAGE"] }
        }

        response = requests.post(url, json=payload, timeout=60)
        result = response.json()

        if "error" in result:
            return jsonify({"error": f"AI 报错: {result['error']['message']}"}), 500

        # 提取图片数据
        image_part = None
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "inlineData" in p:
                    image_part = p["inlineData"]["data"]
                    break

        if image_part:
            return jsonify({"image": image_part})
        else:
            return jsonify({"error": "AI 生成成功但没返回图像数据。"}), 500

    except Exception as e:
        return jsonify({"error": f"连接 AI 失败: {str(e)}"}), 500

if __name__ == '__main__':
    # 🌟 关键：云端服务器会自动分配端口，我们要通过 os.environ.get 获取
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
