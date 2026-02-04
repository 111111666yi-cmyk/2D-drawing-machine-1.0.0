from flask import Flask, render_template

# 初始化 Flask 应用
app = Flask(__name__)

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("==================================================")
    print("   二次元绘图机 v1.0.0 (Standard Edition)   ")
    print("   服务器已启动，请在浏览器访问下方地址：   ")
    print("   http://127.0.0.1:5000   ")
    print("==================================================")
    # 启动服务
    app.run(debug=True, port=5000)