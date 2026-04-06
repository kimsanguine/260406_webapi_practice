# 공공 Web API 실습 프로젝트

공공데이터포털 3종 API(우체국·기상청·에어코리아)를 활용한 강의용 실습 프로젝트.

## 구조

```
260406_webapi_practice/
├── PRD.md                      # 요구사항 정의서
├── requirements.txt
├── .env.example                # API Key 환경변수 예시
├── notebooks/
│   └── WebAPI실습_수정본.ipynb  # 원본 노트북
├── fixed/
│   └── webapi_fixed.ipynb      # 버그 수정 노트북
├── api/
│   ├── address.py              # 우체국 주소 검색
│   ├── weather.py              # 기상청 초단기실황
│   └── airkorea.py             # 에어코리아 대기측정소
└── streamlit/
    └── app.py                  # 인터랙티브 데모 앱
```

## 설치 및 실행

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. API Key 설정
cp .env.example .env
# .env 파일에 실제 SERVICE_KEY 입력

# 4. Streamlit 앱 실행
streamlit run streamlit/app.py
```

## 사용 API

| API | 제공처 | 응답 형식 |
|-----|--------|-----------|
| 주소 검색 | 우체국 | XML |
| 초단기실황 | 기상청 | JSON |
| TM 좌표·측정소 | 에어코리아 | JSON |
