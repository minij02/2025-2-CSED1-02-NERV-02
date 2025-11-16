import uvicorn
from fastapi import FastAPI

# FastAPI 앱 인스턴스 생성
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Filter API is running!", "version": "0.1.0"}

# TODO: 댓글 필터링을 요청받는 API 엔드포인트 추가

# 디버깅
if __name__ == "__main__":
    print("--- [Debug Mode] Filter API starting... ---")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)