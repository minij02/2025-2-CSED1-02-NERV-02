import os
import json
import re
from konlpy.tag import Okt

class FirstPassFilter:
    def __init__(self):
        print("[System] 1차 필터 리소스 로딩 시작...")
        
        # 1. 형태소 분석기 초기화 (메모리 로드)
        self.okt = Okt()
        
        # 2. 경로 설정
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.dict_dir = os.path.join(self.base_dir, 'resources', 'dictionaries')
        
        # 3. 사전 데이터 로드 (메모리에 캐싱)
        self.user_whitelist = set()
        self.user_blacklist = set()
        self.system_dictionary = set()
        
        self._load_user_dictionary(os.path.join(self.dict_dir, 'user_dictionary.json'))
        self._load_system_dictionary(os.path.join(self.dict_dir, 'word_dictionary.json'))
        
        print("[System] 1차 필터 준비 완료.")

    def _load_user_dictionary(self, filepath):
        """내부 메서드: 사용자 사전 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.user_whitelist = set(w.strip().lower() for w in data.get("user_whitelist", []))
                self.user_blacklist = set(w.strip().lower() for w in data.get("user_blacklist", []))
            print(f"  ㄴ 사용자 사전 로드됨: 화이트({len(self.user_whitelist)}), 블랙({len(self.user_blacklist)})")
        except Exception as e:
            print(f"  [Error] 사용자 사전 로드 실패: {e}")

    def _load_system_dictionary(self, filepath):
        """내부 메서드: 시스템 사전 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for category, content in data.items():
                    # 단어들을 시스템 사전에 추가
                    for word in content.get("words", []):
                        self.system_dictionary.add(word.strip().lower())
                    # 시스템 사전 내의 'white' 리스트도 처리하려면 여기에 로직 추가 가능
            print(f"  ㄴ 시스템 사전 로드됨: {len(self.system_dictionary)}개 단어")
        except Exception as e:
            print(f"  [Error] 시스템 사전 로드 실패: {e}")

    def normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text)
        return text

    def execute(self, original_text: str) -> dict:
        """외부에서 호출하는 메인 메서드"""
        status = "PASSED"
        
        # 1. 정규화
        normalized_text = self.normalize_text(original_text)
        
        # 2. 형태소 분석 (self.okt 사용)
        tokened_text = self.okt.pos(normalized_text)
        
        text_for_filtering = normalized_text
        detected_words = []

        for word, pos in tokened_text:
            word_lower = word.lower() # 혹시 몰라 한 번 더 소문자 처리

            # [A] 화이트리스트
            if word_lower in self.user_whitelist:
                text_for_filtering = text_for_filtering.replace(word, "__W__")
                continue

            # [B] 블랙리스트
            if word_lower in self.user_blacklist:
                detected_words.append({'word': word, 'type': 'USER_BLACKLIST'})
                text_for_filtering = text_for_filtering.replace(word, "__B__")
                continue
            
            # [C] 시스템 사전
            if word_lower in self.system_dictionary:
                detected_words.append({'word': word, 'type': 'SYSTEM_KEYWORD'})
                text_for_filtering = text_for_filtering.replace(word, "__F__")
                continue

        if detected_words:
            status = 'FILTERED_BY_FIRST_PASS'
        
        return {
            'original_text': original_text,
            'status': status,
            'detected_words': detected_words,
            'text_for_filtering': text_for_filtering
        }

if __name__ == "__main__":
    import json

    print("==========================================")
    print("▶ [Debug] FirstPassFilter 독립 실행 테스트")
    print("==========================================")

    # 1. 클래스 인스턴스 생성 (이때 사전 로드됨)
    filter_instance = FirstPassFilter()
    
    # 2. 테스트 케이스
    test_comments = [
        "유튜버 개새끼",          # 사용자 블랙리스트 (USER_BLACKLIST)
        "유튜버 천사",            # 사용자 화이트리스트 (허용 -> __W__)
        "유튜버 씨발",            # 시스템 욕설 (SYSTEM_KEYWORD)
        "씨#!@#@#@#발 새끼",     # 특수문자 섞인 욕설 (정규화 후 차단)
        "안녕하세요 좋은 하루",      # 정상
        "이거 개노잼이네"          # 욕설은 아니지만 2차 필터 감 (PENDING_AI)
    ]
    
    # 3. 테스트 실행
    for comment in test_comments:
        print(f"\n[Input] : {comment}")
        
        # 클래스의 메서드 호출
        result = filter_instance.execute(comment)
        
        # 결과 출력 (JSON 형태로 예쁘게)
        print("[Result]:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        print("-" * 40)