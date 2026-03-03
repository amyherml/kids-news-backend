from flask import Flask, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # 允许你的App访问

# 模拟新闻数据（实际使用时替换为你的ChatGPT逻辑）
NEWS_DATA = {
    "generated_at": datetime.now().isoformat(),
    "news": [
        {
            "title": "科学家发现新的海洋生物",
            "category": "科学",
            "whatIsHappening": "在深海发现了会发光的鱼...",
            "funFact": "这种鱼可以用光来交流！"
        },
        {
            "title": "国际空间站新发现",
            "category": "太空",
            "whatIsHappening": "宇航员发现了新的星系...",
            "funFact": "宇宙中有超过1000亿个星系！"
        }
    ]
}

@app.route('/')
def home():
    return "Kids News API is running!"

@app.route('/api/news', methods=['GET'])
def get_news():
    """App获取新闻的接口"""
    return jsonify(NEWS_DATA)

@app.route('/health', methods=['GET'])
def health():
    """健康检查，用于防止休眠"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)