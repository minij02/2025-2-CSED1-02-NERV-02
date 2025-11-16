import os
import json
from korcen import check as korcen

# 사용자 사전 로드
def load_user_dictionary(filepath):
    whitelist = set()
    blacklist = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f) # JSON 파일 로드 (하나의 큰 객체)
            
            # 1. 화이트리스트 가져오기
            whitelist_from_json = data["user_whitelist"]
            for word in whitelist_from_json:
                whitelist.add(word.strip().lower())
        
            # 2. 블랙리스트 가져오기
            blacklist_from_json = data["user_blacklist"]
            for word in blacklist_from_json:
                blacklist.add(word.strip().lower())
                        
        print(f"화이트리스트 {len(whitelist)}개 로드 완료.")
        print(f"블랙리스트 {len(blacklist)}개 로드 완료.")
        
    except FileNotFoundError:
        print(f"사용자 정의 사전 파일을 찾을 수 없습니다: {filepath}.")
    except Exception as e:
        print(f"사전 파일 로드 중 알 수 없는 오류 발생 {filepath}: {e}")
        
    return whitelist, blacklist

# 사전이 정의된 /resources 폴더 경로 계산
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DICTIONARIES_DIR = os.path.join(BASE_DIR, 'resources', 'dictionaries') 

USER_WHITELIST, USER_BLACKLIST = load_user_dictionary(
    os.path.join(DICTIONARIES_DIR, 'user_dictionary.json')
)

# 키워드 검사
def check_keyword(text_for_filtering: str) -> dict:
    # 1차 필터링 과정에서 키워드로 금칙어를 탐지한 경우 --> Type 1 (명백한 악성)
    if korcen.check(text_for_filtering): 
        
        # import 오류
        # detected_words = korcen.highlight(text_for_filtering)
    
        return { 
            'status': 'FLAGGED_KEYWORD', 
            'violation_type': 'FLAGGED_KEYWORD', # 위의 오류로 인한 임시 타입
            'text_for_filtering': text_for_filtering
        }
    
    # 금칙어가 탐지되지 않았거나 판별이 애매한 경우 --> AI 2차 필터링 대기
    return { 
        'status': 'PENDING_AI',
        'violation_type': None,
        'text_for_filtering': text_for_filtering
    }


# 1차 필터링
def execute_first_pass(original_text: str) -> dict:
    """
    1차 필터링 로직을 실행하고 결과를 반환합니다.
    (이 함수는 'USER_WHITELIST'가 .txt, .json, .csv 중 어디서 왔는지 몰라도 됩니다!)
    """
    
    # 1. 텍스트 정규화 (현재는 임시로 소문자 변환 및 양쪽 공백 제거만 진행)
    #    실제 서비스에서는 이 부분에 외부 라이브러리를 활용한 정규화 작업이 적용
    text = original_text.lower().strip()
    
    # 2. 화이트리스트 적용
    text_for_filtering = text
    for white_word in USER_WHITELIST:
        if white_word in text_for_filtering:
            text_for_filtering = text_for_filtering.replace(white_word, "__W__") # 화이트리스트 단어 중화
            
    # 3. 블랙리스트 적용
    for black_word in USER_BLACKLIST:
        if black_word in text_for_filtering: # 중화된 텍스트에서 검사
            return {
                'status': 'FLAGGED_USER_BLACKLIST',
                'violation_type': 'USER_BLACKLIST',
                'text_for_filtering': text_for_filtering
            }

    # 키워드 검사
    filtering_result = check_keyword(text_for_filtering)
    
    return filtering_result

# 디버깅
if __name__ == "__main__":
    
    test_comments = [
        "유튜버 개새끼",          # 화이트리스트에 의해 __W__로 중화
        "유튜버 천사",            # 블랙리스트에 의해 차단
        "유튜버 씨발"             # korcen에 의해 차단
    ]
    
    for comment in test_comments:
        result = execute_first_pass(comment)
        print(f"\nInput: '{comment}'")
        print(f"Result: {result}")