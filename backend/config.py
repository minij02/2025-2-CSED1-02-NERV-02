import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 불러오기
load_dotenv()

# 필터링 강도 설정
# 1: 관찰, 2: 관대함, 3: 일반, 4: 적극, 5: 최대 보호
# 아직 구현 X - 추후 API 요청 시 파라미터로 전달
CURRENT_STRENGTH = int(os.getenv("CURRENT_STRENGTH", 3)) # 기본값 '3' (일반)

# .env 파일에서 YouTube API 키 불러오기
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# AI 모델 경로
# 아직 구현 X - 추후 AI 모델 파일 경로를 지정
BASE_MODEL_PATH = "resources/models/AI_model.h5"