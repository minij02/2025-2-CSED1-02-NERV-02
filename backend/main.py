import sys
import os
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

try:
    import config
    from filter_api.core.first_pass_filter import FirstPassFilter
    from filter_api.core.second_pass_filter import SecondPassFilter
    from filter_api.core.risk_scorer import RiskScorer
    from filter_api.core.policy_manager import PolicyManager
    from filter_api.clients.youtube_client import YouTubeClient
except ImportError as e:
    print(f"[System] 필수 모듈 임포트 실패: {e}")
    sys.exit(1)

app = FastAPI(
    title="YouTube Comment Filtering System API",
    description="1차/2차/위험도/정책 모델을 엄격하게 분리하여 단계별 데이터 변화를 명확히 보여주는 API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# =========================================================
# [Pydantic 모델 정의] - 단계별 엄격한 분리 (Strict Mode)
# =========================================================

# 1. [입력] Raw Text
class TextInput(BaseModel):
    text: str = Field(..., json_schema_extra={
        "example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# --- [Step 1 전용 모델] ---

class FirstPassDetectedWord(BaseModel):
    word: str = Field(..., description="1차 필터가 잡아낸 단어", json_schema_extra={"example": "개새끼"})
    type: str = Field(..., description="감지 유형 (시스템/사용자 사전)", json_schema_extra={"example": "SYSTEM_KEYWORD"})

class FirstPassResponse(BaseModel):
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: str = Field(..., description="1차 필터링 상태", json_schema_extra={"example": "FILTERED_BY_FIRST_PASS"})
    detected_words: List[FirstPassDetectedWord] = Field(..., json_schema_extra={
        "example": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}]
    })
    text_for_filtering: str = Field(..., description="1차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
    })

# --- [Step 2 전용 모델] ---

class SecondPassDetectedWord(BaseModel):
    word: str = Field(..., description="1차 혹은 2차 필터가 잡아낸 단어", json_schema_extra={"example": "010-1234-5678"})
    type: str = Field(..., description="감지 유형 (AI 카테고리 포함)", json_schema_extra={"example": "AI_PRIVACY"})

class SecondPassResponse(BaseModel):
    original_text: str = Field(..., json_schema_extra={"example": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"})
    status: str = Field(..., description="2차 필터링 상태 (누적)", json_schema_extra={"example": "FILTERED_BY_SECOND_PASS"})
    detected_words: List[SecondPassDetectedWord] = Field(..., description="1차+2차 누적 적발 리스트", json_schema_extra={
        "example": [
            {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
            {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
            {"word": "010-1234-5678", "type": "AI_PRIVACY"}
        ]
    })
    text_for_filtering: str = Field(..., description="2차 마스킹 완료된 텍스트", json_schema_extra={
        "example": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
    })

# --- [Step 3 & 4 전용 모델] ---

class RiskResponse(BaseModel):
    risk_score: float = Field(..., description="0.0 ~ 1.0 사이의 위험도 점수", json_schema_extra={"example": 0.98})

class PolicyInput(BaseModel):
    risk_score: float = Field(..., json_schema_extra={"example": 0.98})
    # 정책 결정에는 최종 결과(2차 결과)가 들어가는 것이 맞음
    filter_result: SecondPassResponse 

class PolicyResponse(BaseModel):
    action: str = Field(..., description="최종 처분 결과", json_schema_extra={"example": "AUTO_HIDE"})
    processed_text: str = Field(..., description="최종 노출 텍스트", json_schema_extra={"example": "규정 위반으로 숨겨진 메시지입니다."})
    score: float = Field(..., json_schema_extra={"example": 0.98})

# --- [통합 결과 모델] ---

class AnalysisResult(BaseModel):
    original_text: str
    processed_text: str
    action: str
    score: float
    details: SecondPassResponse # 디테일은 최종 필터링 결과 구조를 따름

# --- [유튜브 리포트 모델] ---

class YoutubeCommentSummary(BaseModel):
    author: str
    published_at: str
    original: str
    processed: str
    action: str
    risk_score: float
    violation_tags: List[str]

class YoutubeAnalysisResponse(BaseModel):
    video_info: Dict[str, str]
    stats: Dict[str, int]
    results: List[YoutubeCommentSummary]


# =========================================================
# [API 1] 개별 모듈 테스트 (Unit APIs)
# =========================================================

@app.post("/api/modules/first-pass", response_model=FirstPassResponse, summary="Step 1. 1차 필터링")
async def run_first_pass(input_data: TextInput):
    """
    KoNLPy 및 사전을 이용한 1차 필터링을 수행합니다.
    반환값은 FirstPassResponse 모델을 따릅니다.
    """
    try:
        result = first_filter.execute(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/second-pass", response_model=SecondPassResponse, summary="Step 2. 2차 필터링 (AI)")
async def run_second_pass(
    first_pass_result: FirstPassResponse = Body(
        ...,
        # [입력 예시] 1차 필터 결과 모델을 그대로 사용 (욕설만 잡힌 상태)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_FIRST_PASS",
                "detected_words": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}],
                "text_for_filtering": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
            }
        }
    )
):
    """
    1차 필터링 결과(FirstPassResponse)를 입력받아 AI 정밀 분석을 수행합니다.
    반환값은 SecondPassResponse 모델을 따르며, AI 적발 내역이 누적됩니다.
    """
    try:
        # Pydantic 모델 -> dict 변환
        input_dict = first_pass_result.dict()
        result = second_filter.execute(input_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/score", response_model=RiskResponse, summary="Step 3. 위험도 점수 계산")
async def calculate_risk_score(
    filter_result: SecondPassResponse = Body(
        ...,
        # [입력 예시] 2차 필터까지 완료된 상태 (모든 적발 내역 포함)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_SECOND_PASS",
                "detected_words": [
                    {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
                    {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
                    {"word": "010-1234-5678", "type": "AI_PRIVACY"}
                ],
                "text_for_filtering": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
            }
        }
    )
):
    try:
        input_dict = filter_result.dict()
        score = risk_scorer.execute(input_dict)
        return {"risk_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/policy", response_model=PolicyResponse, summary="Step 4. 최종 처분 결정")
async def decide_policy(
    data: PolicyInput = Body(
        ...,
        # [입력 예시] 계산된 점수와 최종 필터링 결과
        json_schema_extra={
            "example": {
                "risk_score": 0.98,
                "filter_result": {
                    "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                    "status": "FILTERED_BY_SECOND_PASS",
                    "detected_words": [
                        {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
                        {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
                        {"word": "010-1234-5678", "type": "AI_PRIVACY"}
                    ],
                    "text_for_filtering": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
                }
            }
        }
    )
):
    try:
        score = data.risk_score
        f_res = data.filter_result.dict()
        decision = policy_manager.decide_action(score, f_res)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- [YouTube 단순 조회용 API] ---

@app.get("/api/modules/youtube/video", summary="유튜브 영상 메타데이터 조회")
async def get_youtube_video_info(video_id: str):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")
    return yt_client.get_video_details(video_id)

@app.get("/api/modules/youtube/comments", summary="유튜브 댓글 수집 (원문)")
async def get_youtube_comments_raw(video_id: str, max_pages: int = 1):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")
    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    return {"video_id": video_id, "total_count": len(comments), "comments": comments}

# =========================================================
# [API 2] 전체 통합 워크플로우 (Workflow APIs)
# =========================================================

def _run_pipeline(text: str) -> dict:
    res = first_filter.execute(text)
    res = second_filter.execute(res)
    score = risk_scorer.execute(res)
    final_decision = policy_manager.decide_action(score, res)
    
    return {
        "original_text": res['original_text'],
        "processed_text": final_decision['processed_text'],
        "action": final_decision['action'],
        "score": score,
        "details": res
    }

@app.post("/api/workflow/analyze-text", response_model=AnalysisResult, summary="단일 텍스트 전체 분석")
async def analyze_single_text(
    input_data: TextInput = Body(
        ...,
        json_schema_extra={
            "example": {"text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"}
        }
    )
):
    try:
        result = _run_pipeline(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflow/analyze-youtube", response_model=YoutubeAnalysisResponse, summary="유튜브 영상 댓글 분석")
async def analyze_youtube_video(video_id: str, max_pages: int = 1):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 연결 실패 (API Key 확인 필요)")
    
    video_info = yt_client.get_video_details(video_id)
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
        "video_info": {"title": video_info.get('snippet', {}).get('title', 'Unknown'), "id": video_id},
        "stats": {"total_comments": len(comments), "blocked_comments": blocked_count, "clean_comments": len(comments) - blocked_count},
        "results": analyzed_results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)