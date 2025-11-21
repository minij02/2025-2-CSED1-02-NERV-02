import json
import openai
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

class SecondPassFilter:
    def __init__(self, api_key=None):
        self.client = openai.OpenAI()    
        self.special_ai_modules = config.SPECIAL_AI_MODULES
        self.basic_ai_module = config.BASIC_AI_MODULE

    def _construct_prompt(self, text):
        """
        [프롬프트 생성 담당] 질문 텍스트를 만듭니다.
        """
        check_list = []
        for rule in self.basic_ai_module:
            check_list.append(f"- [기본검사] {rule}")
        for category, rule in self.special_ai_modules.items():
            check_list.append(f"- [{category}] {rule}")

        criteria = "\n".join(check_list)

        return f"""
        분석할 댓글: "{text}"
        
        [판단 기준]
        다음의 모든 기준을 적용하여 엄격하게 검사하세요:
        {criteria}
        
        위 댓글에서 위반되는 '구체적인 부분(단어, 구문)'을 모두 찾아내어 아래 JSON 형식으로 응답하세요.
        각 적발 항목에 대해 가장 적합한 모듈(Category)을 지정해야 합니다.
        
        {{
            "detected_items": [
                {{
                    "keyword": "문제된 단어/구문",
                    "category": "위반 모듈명 (예: PRIVACY, SEXUAL)"
                }}
            ],
            "reason": "판단 사유",
            "severity": integer (1~5)
        }}
        """

    def _call_openai_api(self, prompt):
        """
        [API 통신 담당] 실제 GPT에게 질문을 던지고 JSON 결과를 받아옵니다.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # 또는 "gpt-3.5-turbo" (가성비 모델)
                messages=[
                    {"role": "system", "content": "You are a strict content moderator. Output in JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}, # JSON 모드 강제 (중요)
                temperature=0.0 # 일관된 분석을 위해 0으로 설정
            )
            content = response.choices[0].message.content
            if not content:
                return {}
            return json.loads(content)
            
        except Exception as e:
            print(f"OpenAI API 호출 실패: {e}")
            return {} # 실패 시 빈 객체 반환하여 로직이 안 터지게 함

    def execute(self, first_pass_result):
        """
        메인 실행 함수
        """
        second_pass_result = first_pass_result

        try:
            # 1. 프롬프트 생성
            prompt_text = self._construct_prompt(second_pass_result.get('text_for_filtering', ''))
            
            # 2. API 호출
            gpt_response = self._call_openai_api(prompt_text)

            # 3. 결과 처리
            ai_detected_items = gpt_response.get('detected_items', [])
            
            if ai_detected_items:
                second_pass_result['status'] = "FILTERED_BY_SECOND_PASS"

                for item in ai_detected_items:
                    word = item.get('keyword', '')
                    category = item.get('category', 'DETECTED')
                    
                    if word:
                        # 리스트에 추가
                        second_pass_result['detected_words'].append({
                            "word": word,
                            "type": f"AI_{category.upper()}"
                        })
                        
                        # 텍스트 수정
                        second_pass_result['text_for_filtering'] = second_pass_result['text_for_filtering'].replace(word, "__S__")

            return second_pass_result

        except Exception as e:
            print(f"2차 필터 에러: {e}")
            return first_pass_result