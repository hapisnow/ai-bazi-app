import os
import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Vercel 环境变量
API_KEY = os.environ.get("GEMINI_API_KEY")

# 模型配置
MODEL_NAME = "gemma-3-4b-it"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 简易内存数据库 ---
# 格式: { "用户ID": 剩余可用次数(int) }
invite_db = {}

# --- 数据模型 ---
class DivinationRequest(BaseModel):
    name: str
    gender: int
    birth_year: int
    birth_month: int
    birth_day: int
    birth_hour: int
    event: str
    bazi_json: dict

class InviteRequest(BaseModel):
    ref_id: str  # 用户ID

# --- 邀请功能接口 ---

@app.post("/api/invite/record")
async def record_invite(req: InviteRequest):
    """当朋友点开链接时调用，给邀请人增加1次机会"""
    ref_id = req.ref_id
    if ref_id:
        if ref_id not in invite_db:
            invite_db[ref_id] = 0
        invite_db[ref_id] += 1
        print(f"🎉 邀请成功！用户 {ref_id} 获得1次机会，当前总计: {invite_db[ref_id]}")
    return {"status": "ok"}

@app.get("/api/invite/check")
async def check_status(my_id: str):
    """查询我有几次可用机会"""
    count = invite_db.get(my_id, 0)
    return {"count": count}

@app.post("/api/invite/consume")
async def consume_invite(req: InviteRequest):
    """消耗1次机会进行解锁"""
    uid = req.ref_id
    count = invite_db.get(uid, 0)
    
    if count > 0:
        invite_db[uid] -= 1
        print(f"✅ 用户 {uid} 消耗了1次机会，剩余: {invite_db[uid]}")
        return {"success": True, "remaining": invite_db[uid]}
    else:
        return {"success": False, "message": "次数不足"}

# --- 原有的算命接口 ---

@app.post("/api/analyze")
async def analyze(req: DivinationRequest):
    if not API_KEY:
        return {"score":0, "level":"配置错", "core_text": "API Key 未配置", "pros":[], "cons":[]}

    user_event = req.event.strip()
    if not user_event:
        user_event = "请分析该命主 2025 年的整体流年运势（事业、财运、健康），并给出综合建议。"

    prompt_text = f"""
    Role: Professional Fortune Teller & Data Analyst.
    User: {req.name}, Gender:{req.gender} (1=Male, 0=Female), Birth:{req.birth_year}-{req.birth_month}-{req.birth_day} Hour:{req.birth_hour}.
    Question: {user_event}
    
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
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            try:
                raw = data['candidates'][0]['content']['parts'][0]['text']
                clean = raw.replace("```json", "").replace("```", "").strip()
                if "{" not in clean: raise Exception("No JSON found")
                clean = clean[clean.find("{"):clean.rfind("}")+1]
                return json.loads(clean)
            except Exception as e:
                return {"score":0, "level":"解析错", "core_text": "天机晦涩，数据解析异常，请重试。", "life_trend": []}
        else:
            return {"score":0, "level":"API错", "core_text": f"Google拒绝: {response.status_code}", "life_trend": []}

    except Exception as e:
        return {"score":0, "level":"系统错", "core_text": str(e), "life_trend": []}
