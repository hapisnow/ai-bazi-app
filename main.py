import os
import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Vercel 环境变量
API_KEY = os.environ.get("GEMINI_API_KEY")

# 模型：Gemma 3 (速度快，效果好)
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
        return {"score":0, "level":"配置错", "core_text": "API Key 未配置", "pros":[], "cons":[]}

    # 逻辑：如果前端没传问题，后端自动补全为“流年运势”
    user_event = req.event.strip()
    if not user_event:
        user_event = "请分析该命主 2025 年的整体流年运势（事业、财运、健康），并给出综合建议。"

    prompt_text = f"""
    Role: Professional Fortune Teller.
    User: {req.name}, Gender:{req.gender}, Birth:{req.birth_year}-{req.birth_month}-{req.birth_day} {req.birth_hour}h.
    Question: {user_event}
    
    Requirement: Return VALID JSON ONLY. No markdown.
    Structure:
    {{
        "score": 88,
        "level": "吉",
        "relation": "五行相生",
        "core_text": "简练的中文分析(100字以内)...",
        "pros": ["有利点1", "有利点2"],
        "cons": ["风险点1", "风险点2"],
        "life_trend": [60, 70, 80, 90, 80, 70],
        "paid_content": {{ "soul": "", "strategy": "", "dates": [], "avatar": "" }}
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        response = requests.post(url, json=payload, timeout=50)
        
        if response.status_code == 200:
            data = response.json()
            try:
                raw = data['candidates'][0]['content']['parts'][0]['text']
                clean = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
            except:
                return {"score":0, "level":"解析错", "core_text": "AI 返回数据格式异常", "pros":[], "cons":[]}
        else:
            return {"score":0, "level":"API错", "core_text": f"Google拒绝: {response.status_code}", "pros":[], "cons":[]}

    except Exception as e:
        return {"score":0, "level":"系统错", "core_text": str(e), "pros":[], "cons":[]}
