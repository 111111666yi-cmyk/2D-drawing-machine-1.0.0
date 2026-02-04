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
# 🎨 终极风格预设库 (Style Library)
# ==========================================
STYLES = {
    "default": "anime style, masterpiece, best quality, ultra-detailed, 8k wallpaper, beautiful detailed eyes, beautiful detailed face",
    
    # ─── 绘画技法 ───
    "impasto": "impasto, thick painting, oil painting, brush strokes, rich colors, dimensional, texture, game concept art",
    "cel_shading": "cel shading, flat color, clean lines, anime screencap, minimalist, vibrant, sharp shadows, japanese anime style",
    "watercolor": "watercolor, wet media, soft edges, splatter, color bleed, gentle, healing atmosphere, artistic",
    "sketch": "sketch, pencil sketch, monochrome, lineart, rough lines, cross-hatching, artistic, graphite",
    "ink": "ink wash painting, sumi-e, calligraphy brush, black and white, traditional art, abstract, flowing ink",
    "pixel": "pixel art, 16-bit, dot art, retro game, low res, nostalgic, sprite sheet style",
    
    # ─── 知名画师风格 ───
    "wlop": "WLOP style, fantasy, ethereal, highly detailed, dynamic lighting, princess, cinematic, wind effects",
    "guweiz": "Guweiz style, cool color palette, urban samurai, storytelling, dramatic shadow, sharp focus, desaturated",
    "ask": "Ask style, soft colors, delicate flat shading, floral background, gentle gaze, illustration",
    "mika_pikazo": "Mika Pikazo style, vivid colors, pop art, geometric patterns, energetic, fashion, chaotic color theory",
    "ilya": "Ilya Kuvshinov style, modern pop, focus on eyes and makeup, stylish, trendy, depth of field",
    "redjuice": "Redjuice style, sci-fi, metallic texture, guilty crown style, sharp details, futuristic",
    "mucha": "Alphonse Mucha style, art nouveau, intricate floral decoration, stained glass, elegant curves, golden halo",
    "clamp": "Clamp style, 90s anime, long legs, gorgeous costumes, dramatic wind, shoujo manga, feathers",
    "kantoku": "Kantoku style, plaid patterns, transparency, vibrant lighting, cute, moe, school uniform",
    "kei_mochizuki": "Kei Mochizuki style, unique sharp lines, decadent cute, stylized anatomy, cool vibe",
    "tiv": "Tiv style, standard moe anime, soft lighting, emotional, korean illustrator style",

    # ─── 氛围美学 ───
    "cyberpunk": "cyberpunk, neon lights, mechanical parts, hologram, futuristic city, chromatic aberration, rain, night",
    "steampunk": "steampunk, gears, brass, goggles, victorian era, clockwork, sepia tone, steam engine",
    "gothic": "gothic lolita, dark fantasy, somber atmosphere, church, stained glass, ruins, mystery, roses",
    "vaporwave": "vaporwave, retro 80s anime, neon pastel, glitch effect, vhs artifact, city pop, lo-fi, palm trees",
    "dreamy": "pastel colors, dreamy, fairy tale, soft light, fluffy, kawaii, marshmallows, sparkles"
}

# ==========================================
# ✨ 光影与视角增强包 (Lighting & Camera)
# ==========================================
LIGHTING_FX = {
    "none": "",
    "cinematic": "cinematic lighting, dramatic atmosphere, movie scene, depth of field, 35mm lens",
    "volumetric": "volumetric lighting, god rays, tyndall effect, misty atmosphere, sun shafts",
    "bioluminescence": "bioluminescence, glowing particles, magical forest, night scene, ethereal glow, neon details",
    "raytracing": "ray tracing, realistic reflections, glossy surfaces, global illumination, unreal engine 5 render",
    "rim_light": "rim light, back lighting, silhouette, hair glowing, separation from background",
    
    "fisheye": "fisheye lens, wide angle, distorted perspective, dynamic action, nose close-up",
    "dutch": "dutch angle, tilted camera, dynamic composition, tension",
    "close_up": "extreme close-up, macro photography, detailed iris, eyelashes, emotional expression",
    "full_body": "full body shot, wide shot, showing shoes, standing pose, environment view"
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
        mode = data.get('mode', 'txt2img') # txt2img, lineart, colorize
        style_key = data.get('style', 'default')
        lighting_key = data.get('lighting', 'none')
        user_key = data.get('api_key', '').strip()
        
        # 🎲 种子控制
        seed = data.get('seed')
        if seed is None or seed == "":
            seed = random.randint(0, 10000000)
        else:
            seed = int(seed)

        logger.info(f"请求: {provider} | 模式: {mode} | 风格: {style_key} | 种子: {seed}")

        # 1. 智能构建提示词
        base_quality = "masterpiece, best quality, ultra-detailed, highres"
        style_prompt = STYLES.get(style_key, STYLES['default'])
        lighting_prompt = LIGHTING_FX.get(lighting_key, "")
        
        # 根据模式微调提示词
        mode_prefix = ""
        if mode == 'lineart':
            mode_prefix = "monochrome lineart, black and white, coloring page, clean lines, no background, white background, "
            # 线稿模式下，强制覆盖掉一些可能会产生颜色的风格词
            if "color" in style_prompt: style_prompt = "sketch style, intricate details"
        elif mode == 'colorize':
            mode_prefix = "vibrant colors, no outlines, painting, voluminous, "
        
        final_prompt = f"{base_quality}, {mode_prefix}{style_prompt}, {lighting_prompt}, {user_prompt}"

        # ==========================================
        # 🎁 游客模式 (Pollinations)
        # ==========================================
        if provider == 'guest':
            # 针对 Pollinations 优化 URL
            safe_prompt = final_prompt.replace(' ', '%20')
            image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true&model=any-dark"
            
            try:
                # 服务器代下载，解决前端跨域和速度问题
                resp = requests.get(image_url, timeout=25)
                if resp.status_code == 200:
                    img_b64 = base64.b64encode(resp.content).decode('utf-8')
                    return jsonify({"image_b64": img_b64, "seed": seed})
                # 下载失败则返回 URL 让前端重试
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

        # ==========================================
        # ☁️ Google (备用/图生文)
        # ==========================================
        elif provider == 'google':
             return jsonify({"error": "Google 绘图接口暂未开放，请使用游客模式"}), 400

        return jsonify({"error": "Invalid provider"}), 400

    except Exception as e:
        logger.error(f"Crash: {e}")
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
