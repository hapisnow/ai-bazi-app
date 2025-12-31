import os
import json
import uvicorn
import requests
import urllib3
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# 1. 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 配置区域 ---
API_KEY = "AIzaSyCxIJHDkCE7ZR_2IGcgz3lRIFq2g0ezczM" 

# 代理配置
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897"
}

# 指定模型: Gemma 3
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
    print(f"--- 收到请求: {req.name} (模型: {MODEL_NAME}) ---")
    
    prompt_text = f"""
    Role: Chinese BaZi Fortune Teller.
    User: {req.name}, {req.gender}, {req.birth_year}-{req.birth_month}-{req.birth_day} {req.birth_hour}h.
    BaZi: {json.dumps(req.bazi_json, ensure_ascii=False)}
    Question: {req.event}
    
    Return JSON ONLY. No Markdown.
    {{
        "score": 88,
        "level": "吉",
        "relation": "相生",
        "core_text": "100 words concise analysis...",
        "pros": ["Pro1", "Pro2"],
        "cons": ["Con1", "Con2"],
        "life_trend": [60, 75, 80, 85, 70, 65],
        "paid_content": {{ "soul": "...", "strategy": "...", "dates": ["..."], "avatar": "..." }}
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    # ---------------------------------------------------------
    # 👇 重点在这里：我已经帮你把 URL 里的脏字符全部清理干净了
    # ---------------------------------------------------------
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

    try:
        print(f"⚡️ 正在呼叫 {MODEL_NAME} ...")
        
        response = requests.post(
            url, 
            json=payload, 
            proxies=PROXIES, 
            timeout=30, 
            verify=False
        )
        
        if response.status_code == 200:
            print(f"🎉 生成成功！")
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        
        else:
            print(f"❌ API 报错: {response.status_code} - {response.text}")
            return {"score":0, "level":"报错", "core_text": f"Google拒绝: {response.status_code}", "life_trend":[]}

    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return {"score":0, "level":"系统错误", "core_text": "连接中断，请检查VPN。", "life_trend":[]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)