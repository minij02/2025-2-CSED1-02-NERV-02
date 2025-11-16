from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sys
import os

# config.py를 찾기 위한 경로 설정
current_dir = os.path.dirname(__file__)
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(backend_dir)

try:
    import config
except ImportError:
    print("Error: config.py를 찾을 수 없습니다.", file=sys.stderr)
    print(f"Current Path: {sys.path}", file=sys.stderr)
    sys.exit(1)


# 1. YouTube API 서비스 빌드
def get_youtube_service():
    # config에서 API 키 로드
    api_key = config.YOUTUBE_API_KEY
    # 키가 설정되지 않았거나 기본값이면 오류
    if not api_key or api_key == "YOUR_ACTUAL_API_KEY_HERE":
        print("Error: YouTube API Key가 config.py에 설정되지 않았거나 유효하지 않습니다.", file=sys.stderr)
        print("backend/.env 파일에 키를 입력했는지 확인하세요.", file=sys.stderr)
        return None
      
    try:
        # YouTube API 서비스 빌드
        youtube_service = build('youtube', 'v3', developerKey=api_key)
        return youtube_service 
    except Exception as e:
        print(f"YouTube 서비스 빌드 중 오류 발생: {e}", file=sys.stderr)
        return None

# 2. 영상 메타데이터 수집
def get_video_details(youtube, video_id):
    try:
        # 영상 메타데이터 요청
        request = youtube.videos().list(
            part="snippet,topicDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            print(f"Error: ID {video_id}에 해당하는 비디오를 찾을 수 없습니다.", file=sys.stderr)
            return None

        # 응답 파싱
        item = response['items'][0]
        snippet = item.get('snippet', {})
        topic_details = item.get('topicDetails', {})

        # 'snippet': 영상의 제목, 설명, 태그 등 "표면적인" 기본 정보
        # 'topicDetails': Google이 이 영상을 '무엇'에 대한 영상인지 분석한 "주제" 정보
        video_info = {
            "snippet": {
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "tags": snippet.get("tags", []),
                "categoryId": snippet.get("categoryId"),
            },
            "topicDetails": {
                "topicCategories": topic_details.get("topicCategories", [])
            }
        }
        return video_info

    except HttpError as e:
        print(f"HTTP Error {e.resp.status}: {e.content}", file=sys.stderr)
        if e.resp.status == 403:
             print("API 할당량이 초과되었거나 키가 유효하지 않을 수 있습니다.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}", file=sys.stderr)
        return None

# 3. 댓글 데이터 수집 
def get_comments(youtube, video_id, max_pages=1):
    comments_list = []
    
    try:
        # 댓글 데이터 요청
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100, # 페이지 당 최대 100개
            order="relevance" # 또는 'time'
        )
        
        page_count = 0
        while request and page_count < max_pages:
            response = request.execute()
            
            # 응답 파싱
            for item in response['items']:
                snippet = item['snippet']['topLevelComment']['snippet']
                comments_list.append({
                    "comment_id": item['id'],
                    "text_original": snippet['textOriginal'],
                    "author_display_name": snippet.get('authorDisplayName'),
                    "published_at": snippet['publishedAt'],
                })
            
            # 다음 페이지 요청
            request = youtube.commentThreads().list_next(
                previous_request=request, 
                previous_response=response
            )
            page_count += 1

        return comments_list

    except HttpError as e:
        print(f"HTTP Error {e.resp.status}: {e.content}", file=sys.stderr)
        if e.resp.status == 403:
            if "commentsDisabled" in str(e.content):
                print(f"비디오 ID {video_id}의 댓글이 비활성화되었습니다.", file=sys.stderr)
            else:
                print("API 할당량이 초과되었거나 키가 유효하지 않을 수 있습니다.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}", file=sys.stderr)
        return []