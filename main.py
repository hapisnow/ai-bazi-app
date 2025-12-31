import os
import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Vercel 环境变量
API_KEY = os.environ.get("GEMINI_API_KEY")

# 模型：Gemma 3 (速度快，不仅能算命，还能生成图表数据)
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
    is_overall = False
    if not user_event:
        user_event = "请分析该命主 2025 年的整体流年运势（事业、财运、健康），并给出综合建议。"
        is_overall = True

    print(f"收到请求: {req.name}, 问题: {user_event}")

    # 核心提示词：要求 AI 返回符合前端图表结构的 JSON
    prompt_text = f"""
    Role: Professional Fortune Teller & Data Analyst.
    User: {req.name}, Gender:{req.gender} (1=Male, 0=Female), Birth:{req.birth_year}-{req.birth_month}-{req.birth_day} Hour:{req.birth_hour}.
    Question: {user_event}
    
    Task: Analyze the BaZi and generate a JSON response for a fortune-telling app.
    
    Requirement: Return VALID JSON ONLY. No markdown.
    The JSON must match this structure EXACTLY:
    {{
        "score": 88,
        "level": "吉", 
        "relation": "五行相生",
        "core_text": "Brief analysis (under 100 words) in Chinese. Be mystical yet encouraging.",
        "pros": ["Advantage 1", "Advantage 2", "Advantage 3"],
        "cons": ["Risk 1", "Risk 2", "Risk 3"],
        "life_trend": [
            {{ "age": "2025", "kw": "关键词1", "val": 75, "desc": "2025年运势简述...", "adv": "建议..." }},
            {{ "age": "2026", "kw": "关键词2", "val": 80, "desc": "2026年运势简述...", "adv": "建议..." }},
            {{ "age": "2027", "kw": "关键词3", "val": 65, "desc": "2027年运势简述...", "adv": "建议..." }},
            {{ "age": "2030", "kw": "大运交接", "val": 85, "desc": "未来展望...", "adv": "建议..." }},
            {{ "age": "2035", "kw": "事业巅峰", "val": 90, "desc": "远期预测...", "adv": "建议..." }},
            {{ "age": "晚年", "kw": "归藏", "val": 70, "desc": "晚运简述...", "adv": "建议..." }}
        ]
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        # 设置超时为 60秒，给 AI 足够时间生成复杂 JSON
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            try:
                raw = data['candidates'][0]['content']['parts'][0]['text']
                # 强力清洗 JSON
                clean = raw.replace("```json", "").replace("```", "").strip()
                if "{" not in clean: raise Exception("No JSON found")
                clean = clean[clean.find("{"):clean.rfind("}")+1]
                return json.loads(clean)
            except Exception as e:
                print(f"解析失败: {e}")
                return {"score":0, "level":"解析错", "core_text": "天机晦涩，数据解析异常，请重试。", "life_trend": []}
        else:
            return {"score":0, "level":"API错", "core_text": f"Google拒绝: {response.status_code}", "life_trend": []}

    except Exception as e:
        return {"score":0, "level":"系统错", "core_text": str(e), "life_trend": []}
