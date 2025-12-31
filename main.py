import os
import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- 部署版配置 ---
# 1. 优先从环境变量取 Key (部署到 Vercel 必须用这个)
# 2. 如果本地运行，fallback 到硬编码的 Key
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCxIJHDkCE7ZR_2IGcgz3lRIFq2g0ezczM")

# 指定模型
MODEL_NAME = "gemma-3-4b-it"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DivinationRequest(BaseModel):
    name: str
    gender: int
    birth_year: int
    birth_month: int
    birth_day: int
    birth_hour: int
    event: str
    bazi_json: dict

@app.post("/api/analyze")
async def analyze(req: DivinationRequest):
    if not API_KEY:
        return {"score":0, "level":"配置错误", "core_text": "后端未配置 API Key", "life_trend":[]}

    print(f"--- 收到请求: {req.name} ---")
    
    # 🌟 逻辑优化：如果用户没填 event，自动补充默认问题
    user_question = req.event.strip()
    if not user_question:
        user_question = "请分析该命主 2025 年的整体流年运势（事业、财运、感情），并给出综合建议。"

    prompt_text = f"""
    Role: Professional Chinese BaZi Fortune Teller.
    Task: Analyze the user's fortune based on BaZi and the question.
    
    User Profile:
    - Name: {req.name}
    - Gender: {req.gender} (1=Male, 0=Female)
    - Birth: {req.birth_year}-{req.birth_month}-{req.birth_day} Hour: {req.birth_hour}
    - Question/Event: {user_question}
    
    Requirement:
    Return ONLY a valid JSON string. Do not use Markdown code blocks.
    The JSON must match this structure exactly:
    {{
        "score": 85,
        "level": "吉",
        "relation": "五行相生",
        "core_text": "Write a concise analysis (under 100 words) in Chinese. Be encouraging and mystical.",
        "pros": ["Point 1", "Point 2"],
        "cons": ["Risk 1", "Risk 2"],
        "life_trend": [60, 75, 80, 85, 70, 65],
        "paid_content": {{ "soul": "guidance", "strategy": "advice", "dates": ["date1"], "avatar": "suggestion" }}
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

    try:
        # Vercel 服务器在美国，直连 Google，timeout 设置为 45秒 防止稍微慢一点就报错
        response = requests.post(url, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            try:
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception as parse_e:
                print(f"解析失败: {parse_e}")
                return {"score":0, "level":"解析错误", "core_text": "天机晦涩，数据解析异常，请重试。", "life_trend":[]}
        else:
            return {"score":0, "level":"API报错", "core_text": f"Google拒绝连接: {response.status_code}", "life_trend":[]}

    except Exception as e:
