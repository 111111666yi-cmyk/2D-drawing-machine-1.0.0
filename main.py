import os
import random
import logging
import requests
import base64
from flask import Flask, render_template, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 环境变量
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
        image_base64 = data.get('image') 
        
        # 🟢 关键修复：去除 Key 首尾的空格和换行符
        user_key = data.get('api_key', '').strip() if data.get('api_key') else None

        logger.info(f"收到请求: Provider={provider}, Mode={mode}")

        # ==========================================
        # 🎁 方案 A: 游客模式 (服务器代下载加速版)
        # ==========================================
        if provider == 'guest':
            seed = random.randint(0, 1000000)
            # 优化提示词，确保二次元风格
            final_prompt = f"anime style, masterpiece, best quality, {prompt}"
            if mode == 'lineart':
                final_prompt = f"monochrome lineart, sketch, {prompt}"
            
            # 使用 Pollinations 接口
            image_url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&nologo=true&model=any-dark"
            
            logger.info("正在使用 Zeabur 服务器加速下载游客图片...")
            
            # ⚡ 服务器端代理下载 (解决客户端加载慢的问题)
            try:
                # 设置 15 秒超时
                img_resp = requests.get(image_url, timeout=15)
                if img_resp.status_code == 200:
                    # 转为 Base64 直接返回给前端
                    img_b64 = base64.b64encode(img_resp.content).decode('utf-8')
                    return jsonify({"image_b64": img_b64})
                else:
                    return jsonify({"error": "游客绘图引擎暂时繁忙，请重试"}), 502
            except Exception as e:
                logger.error(f"游客模式下载失败: {e}")
                return jsonify({"image_url": image_url}) # 如果服务器下载失败，回退到让前端自己加载

        # ==========================================
        # ☁️ 方案 B: Google Gemini
        # ==========================================
        elif provider == 'google':
            key = user_key if user_key else GOOGLE_API_KEY
            if not key: return jsonify({"error": "未配置 Google Key"}), 400

            # 调试日志：检查 Key 是否读取正确 (只显示前5位)
            logger.info(f"使用 Google Key: {key[:5]}******")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            
            # Gemini 绘图通常需要 Imagen 模型，Flash 主要用于文本/识别
            # 这里保持原逻辑，但建议用户确认 Key 权限
            payload = {
                "contents": [{ "parts": [{"text": f"Draw anime: {prompt}"}] }]
            }
            if image_base64:
                 payload['contents'][0]['parts'].append({"inlineData": {"mimeType": "image/png", "data": image_base64}})

            try:
                resp = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=60)
                res_json = resp.json()
                
                if "error" in res_json:
                    return jsonify({"error": f"Google 报错: {res_json['error']['message']}"}), 500
                
                # 尝试提取图片
                candidates = res_json.get('candidates', [])
                if candidates:
                    for part in candidates[0].get('content', {}).get('parts', []):
                        if 'inlineData' in part:
                            return jsonify({"image_b64": part['inlineData']['data']})
                return jsonify({"error": "Gemini 仅返回了文本，该模型版本可能不支持直接绘图。"}), 500
            except Exception as e:
                return jsonify({"error": f"Google 请求异常: {str(e)}"}), 500

        # ==========================================
        # 🤖 方案 C: OpenAI DALL-E 3
        # ==========================================
        elif provider == 'openai':
            key = user_key if user_key else OPENAI_API_KEY
            if not key: return jsonify({"error": "未配置 OpenAI Key"}), 400
            
            # 🟢 调试日志：关键步骤
            logger.info(f"正在调用 OpenAI, Key 长度: {len(key)}, 前缀: {key[:3]}...")

            try:
                resp = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}" # 这里已经去除了空格
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": f"Anime style artwork, masterpiece. {prompt}",
                        "n": 1,
                        "size": "1024x1024",
                        "response_format": "b64_json"
                    },
                    timeout=60
                )
                res_json = resp.json()
                
                # 精确捕获 OpenAI 错误
                if "error" in res_json:
                    err_msg = res_json['error']['message']
                    err_code = res_json['error'].get('code', 'unknown')
                    logger.error(f"OpenAI Error: {err_msg}")
                    return jsonify({"error": f"OpenAI 拒绝请求 ({err_code}): {err_msg}"}), 500

                return jsonify({"image_b64": res_json['data'][0]['b64_json']})
                
            except Exception as e:
                logger.error(f"OpenAI 网络错误: {e}")
                return jsonify({"error": "连接 OpenAI 超时，请检查网络或稍后再试"}), 500

        return jsonify({"error": "无效的选项"}), 400

    except Exception as e:
        logger.error(f"全局异常: {e}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
