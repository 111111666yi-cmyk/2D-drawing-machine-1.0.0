import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# 读取 Zeabur 后台配置的环境变量
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    # 1. 检查 Zeabur 后台是否填了 Key
    if not GOOGLE_API_KEY:
        return jsonify({"error": "❌ 错误：云端未检测到密钥。请在 Zeabur 的【变量】里添加 GOOGLE_API_KEY。"}), 400

    data = request.json
    mode = data.get('mode', 'txt2img')
    prompt = data.get('prompt', '1girl')
    image_base64 = data.get('image')

    try:
        # 2. 修正模型名称：使用全球通用的 gemini-1.5-flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        
        # 3. 构建指令
        system_instruction = "You are an expert anime artist."
        if mode == "lineart":
            user_msg = "Convert this image into high-quality black and white anime line art."
        elif mode == "colorize":
            user_msg = f"Colorize this line art with a vibrant anime style. Palette: {prompt}"
        elif mode == "redraw":
            user_msg = f"Redraw this image in a high-quality anime style. Details: {prompt}"
        else: # txt2img
            user_msg = f"Draw a high-quality anime illustration: {prompt}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": system_instruction + " " + user_msg},
                    *( [{"inlineData": {"mimeType": "image/png", "data": image_base64}}] if image_base64 else [] )
                ]
            }],
            "generationConfig": { "responseModalities": ["IMAGE"] }
        }

        # 4. 发送请求
        response = requests.post(url, json=payload, timeout=60)
        result = response.json()

        if "error" in result:
            return jsonify({"error": f"Google 报错: {result['error']['message']}"}), 500

        # 5. 提取图片
        try:
            # 兼容不同格式的返回
            candidates = result.get("candidates", [])
            if not candidates:
                return jsonify({"error": "AI 未返回任何内容，请检查 Prompt 是否违规。"}), 500
                
            parts = candidates[0].get("content", {}).get("parts", [])
            image_data = None
            for p in parts:
                if "inlineData" in p:
                    image_data = p["inlineData"]["data"]
                    break
            
            if image_data:
                return jsonify({"image": image_data})
            else:
                return jsonify({"error": "AI 生成成功但被拦截（无图片数据）。"}), 500

        except Exception as e:
            return jsonify({"error": f"解析失败: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Zeabur 必须监听 0.0.0.0 和环境变量 PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
