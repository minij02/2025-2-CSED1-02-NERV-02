import sys
import os
import config
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

# ---------------------------------------------------------
# [임포트 수정] 패키지 구조에 맞게 경로 지정
# ---------------------------------------------------------
try:
    # core 패키지에서 모듈 가져오기
    from filter_api.core.first_pass_filter import FirstPassFilter
    from filter_api.core.second_pass_filter import SecondPassFilter
    from filter_api.core.risk_scorer import RiskScorer
    from filter_api.core.policy_manager import PolicyManager

    # clients 패키지에서 모듈 가져오기
    from filter_api.clients.youtube_client import YouTubeClient
    
except ImportError as e:
    print(f"[System] 필수 모듈 임포트 실패: {e}")
    print("폴더 구조(core/, client/)와 __init__.py 파일이 있는지 확인해주세요.")
    sys.exit(1)

# ---------------------------------------------------------
# [FastAPI 앱 초기화]
# ---------------------------------------------------------
app = FastAPI(
    title="YouTube Comment Filtering System API",
    description="1차/2차 필터링, 위험도 분석, 정책 결정을 수행하는 API 서버",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# [전역 인스턴스 초기화]
# ---------------------------------------------------------
print("[System] 모듈 초기화 중...")
try:
    first_filter = FirstPassFilter()
    second_filter = SecondPassFilter()
    risk_scorer = RiskScorer()
    policy_manager = PolicyManager()
    yt_client = YouTubeClient()
    print("[System] 서버 준비 완료.")
except Exception as e:
    print(f"[System] 초기화 중 오류 발생: {e}")
    sys.exit(1)


# ---------------------------------------------------------
# [Pydantic 모델 정의]
# ---------------------------------------------------------
class TextInput(BaseModel):
    text: str

class FirstPassResult(BaseModel):
    original_text: str
    status: str
    detected_words: List[Dict[str, str]]
    text_for_filtering: str

class AnalysisResult(BaseModel):
    original_text: str
    processed_text: str
    action: str
    score: float
    details: Dict[str, Any]

# ---------------------------------------------------------
# [API 1] 개별 모듈 테스트용 (Unit APIs)
# ---------------------------------------------------------

@app.post("/api/modules/first-pass", summary="1차 필터링")
async def run_first_pass(input_data: TextInput):
    try:
        result = first_filter.execute(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/second-pass", summary="2차 필터링 (AI)")
async def run_second_pass(first_pass_result: FirstPassResult):
    try:
        # Pydantic 모델 -> dict 변환
        input_dict = first_pass_result.dict()
        result = second_filter.execute(input_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/score", summary="위험도 점수 계산")
async def calculate_risk_score(filter_result: FirstPassResult):
    try:
        input_dict = filter_result.dict()
        score = risk_scorer.execute(input_dict)
        return {"risk_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/policy", summary="최종 처분 결정")
async def decide_policy(data: Dict[str, Any]):
    try:
        score = data.get("risk_score")
        f_res = data.get("filter_result")
        
        if score is None or f_res is None:
            raise HTTPException(status_code=400, detail="risk_score와 filter_result가 필요합니다.")
            
        decision = policy_manager.decide_action(score, f_res)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- [YouTube 단순 조회용 API] ---

@app.get("/api/modules/youtube/video", summary="유튜브 영상 메타데이터 조회")
async def get_youtube_video_info(video_id: str):
    # 1. 연결 상태 확인 (yt_client.youtube 객체 확인)
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")

    # 2. 메서드 호출 (서비스 객체 전달 X)
    video_info = yt_client.get_video_details(video_id)
    
    if not video_info:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없거나 접근 권한이 없습니다.")
        
    return video_info

@app.get("/api/modules/youtube/comments", summary="유튜브 댓글 수집 (원문)")
async def get_youtube_comments_raw(video_id: str, max_pages: int = 1):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")

    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    
    return {
        "video_id": video_id,
        "total_count": len(comments),
        "comments": comments
    }

# ---------------------------------------------------------
# [API 2] 전체 통합 워크플로우 (Workflow APIs)
# ---------------------------------------------------------

def _run_pipeline(text: str) -> dict:
    """내부 함수: 파이프라인 실행"""
    # 1. 1차 필터
    res = first_filter.execute(text)
    
    # 2. 2차 필터 (AI) - 항상 실행
    # res = second_filter.execute(res)
    
    # 3. 점수 계산
    score = risk_scorer.execute(res)
    
    # 4. 정책 결정
    final_decision = policy_manager.decide_action(score, res)
    
    return {
        "original_text": res['original_text'],
        "processed_text": final_decision['processed_text'],
        "action": final_decision['action'],
        "score": score,
        "details": res
    }

@app.post("/api/workflow/analyze-text", response_model=AnalysisResult, summary="단일 텍스트 전체 분석")
async def analyze_single_text(input_data: TextInput):
    try:
        result = _run_pipeline(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow/analyze-youtube", summary="유튜브 영상 댓글 분석")
async def analyze_youtube_video(video_id: str, max_pages: int = 1):
    """
    YouTube Video ID를 입력받아 댓글 수집 후 전체 필터링 수행
    """
# 1. 클라이언트 연결 확인
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 연결 실패 (API Key 확인 필요)")
    
    # 2. 영상 정보 가져오기 (메서드 직접 호출)
    video_info = yt_client.get_video_details(video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없거나 정보 로드에 실패했습니다.")
        
    # 3. 댓글 수집
    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    
    analyzed_results = []
    blocked_count = 0
    
    for comm in comments:
        text = comm['text_original']
        analysis = _run_pipeline(text)
        
        summary = {
            "author": comm['author_display_name'],
            "published_at": comm['published_at'],
            "original": text,
            "processed": analysis['processed_text'],
            "action": analysis['action'],
            "risk_score": analysis['score'],
            "violation_tags": [item['type'] for item in analysis['details']['detected_words']]
        }
        analyzed_results.append(summary)
        
        if analysis['action'] != "PASS":
            blocked_count += 1

    return {
        "video_info": {
            "title": video_info['snippet']['title'],
            "id": video_id
        },
        "stats": {
            "total_comments": len(comments),
            "blocked_comments": blocked_count,
            "clean_comments": len(comments) - blocked_count
        },
        "results": analyzed_results
    }

if __name__ == "__main__":
    import uvicorn
    # main.py 파일이 있는 위치에서 실행한다고 가정
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)