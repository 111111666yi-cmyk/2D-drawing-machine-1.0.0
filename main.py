import os
import random
import logging
import requests
import base64
import time
from flask import Flask, render_template, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ==========================================
# 🎨 超级风格预设库 (Style Library)
# ==========================================
STYLES = {
    "default": "anime style, masterpiece, best quality, ultra-detailed, 8k wallpaper, beautiful detailed eyes",
    # ─── 技法流派 ───
    "impasto": "impasto, thick painting, oil painting, brush strokes, rich colors, dimensional, texture",
    "cel_shading": "cel shading, flat color, clean lines, anime screencap, minimalist, vibrant, sharp shadows",
    "watercolor": "watercolor, wet media, soft edges, splatter, color bleed, gentle, healing atmosphere",
    "sketch": "sketch, pencil sketch, monochrome, lineart, rough lines, cross-hatching, artistic",
    "ink": "ink wash painting, sumi-e, calligraphy brush, black and white, traditional art, abstract",
    "pixel": "pixel art, 16-bit, dot art, retro game, low res, nostalgic",
    # ─── 知名画师风格 ───
    "wlop": "WLOP style, fantasy, ethereal, highly detailed, dynamic lighting, princess, cinematic",
    "guweiz": "Guweiz style, cool color palette, urban samurai, storytelling, dramatic shadow, sharp focus",
    "mika_pikazo": "Mika Pikazo style, vivid colors, pop art, geometric patterns, energetic, fashion",
    "alphonse_mucha": "Alphonse Mucha style, art nouveau, intricate floral decoration, stained glass, elegant curves",
    "clamp": "Clamp style, 90s anime, long legs, gorgeous costumes, dramatic wind, shoujo manga",
    # ─── 氛围流派 ───
    "cyberpunk": "cyberpunk, neon lights, mechanical parts, hologram, futuristic city, chromatic aberration, rain",
    "steampunk": "steampunk, gears, brass, goggles, victorian era, clockwork, sepia tone",
    "gothic": "gothic lolita, dark fantasy, somber atmosphere, church, stained glass, ruins, mystery",
    "vaporwave": "vaporwave, retro 80s anime, neon pastel, glitch effect, vhs artifact, city pop, lo-fi",
    "dreamy": "pastel colors, dreamy, fairy tale, soft light, fluffy, kawaii, marshmallows"
}

# ==========================================
# ✨ 光影与视角增强包 (Lighting & Camera)
# ==========================================
LIGHTING_FX = {
    "none": "",
    "cinematic": "cinematic lighting, dramatic atmosphere, movie scene, depth of field",
    "volumetric": "volumetric lighting, god rays, tyndall effect, misty atmosphere",
    "bioluminescence": "bioluminescence, glowing particles, magical forest, night scene, ethereal glow",
    "rembrandt": "rembrandt lighting, chiaroscuro, strong contrast, dramatic shadows",
    "fisheye": "fisheye lens, wide angle, distorted perspective, dynamic action",
    "close_up": "close-up, detailed face, macro photography, emotional expression"
}

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
        if not data: return jsonify({"error": "No data"}), 400

        # 获取前端参数
        provider = data.get('provider', 'guest')
        user_prompt = data.get('prompt', '')
        style_key = data.get('style', 'default')
        lighting_key = data.get('lighting', 'none')
        user_key = data.get('api_key', '').strip()
        
        # 🎲 核心逻辑：种子控制 (实现二次绘图的关键)
        # 如果前端传了 seed (用户点击了"微调")，就用旧的；否则生成新的
        seed = data.get('seed')
        if seed is None or seed == "":
            seed = random.randint(0, 10000000)
        else:
            seed = int(seed) # 锁定种子

        logger.info(f"请求: {provider} | 风格: {style_key} | 种子: {seed}")

        # 1. 组合超级提示词
        # 结构：[质量词] + [风格词] + [光影词] + [用户描述]
        base_quality = "masterpiece, best quality, ultra-detailed, highres"
        style_prompt = STYLES.get(style_key, STYLES['default'])
        lighting_prompt = LIGHTING_FX.get(lighting_key, "")
        
        final_prompt = f"{base_quality}, {style_prompt}, {lighting_prompt}, {user_prompt}"

        # ==========================================
        # 🎁 游客模式 (Pollinations) - 支持种子锁定
        # ==========================================
        if provider == 'guest':
            # Pollinations 完美支持 seed 参数
            image_url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&nologo=true&model=any-dark"
            
            try:
                resp = requests.get(image_url, timeout=25)
                if resp.status_code == 200:
                    img_b64 = base64.b64encode(resp.content).decode('utf-8')
                    # ✅ 返回 image_b64 以及本次使用的 seed，方便前端下次复用
                    return jsonify({"image_b64": img_b64, "seed": seed})
                return jsonify({"image_url": image_url, "seed": seed})
            except Exception as e:
                logger.error(f"Guest timeout: {e}")
                return jsonify({"image_url": image_url, "seed": seed})

        # ==========================================
        # 🤖 OpenAI DALL-E 3
        # ==========================================
        elif provider == 'openai':
            key = user_key if user_key else OPENAI_API_KEY
            if not key: return jsonify({"error": "请输入 OpenAI Key"}), 400

            try:
                # 注意：DALL-E 3 API 不直接支持 seed 参数来固定画面
                # 但我们可以把 style 强行写入 prompt 来尽可能保持一致
                resp = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                    json={
                        "model": "dall-e-3",
                        "prompt": final_prompt,
                        "n": 1, 
                        "size": "1024x1024",
                        "response_format": "b64_json",
                        "quality": "standard" 
                    },
                    timeout=55
                )
                res_json = resp.json()
                if "error" in res_json:
                    return jsonify({"error": res_json['error']['message']}), 500
                
                return jsonify({"image_b64": res_json['data'][0]['b64_json'], "seed": seed})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        return jsonify({"error": "Invalid provider"}), 400

    except Exception as e:
        logger.error(f"Crash: {e}")
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
