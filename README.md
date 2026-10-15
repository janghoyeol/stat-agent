# stat-agent

자연어로 질문하면 국가통계포털(KOSIS)에서 알맞은 통계표를 찾아 수치를 조회하고,
**출처와 함께** 답하는 AI 에이전트.

> 예) "평택시 인구는 최근 3년간 어떻게 변했어?"
> → 통계표 검색 → 항목·지역 코드 확인 → 수치 조회 → 증감률 계산 → 출처 포함 답변

## 차별점 (목표)
- 모든 숫자에 출처(통계표명, 기준 시점, KOSIS 링크)를 붙인다. 못 찾으면 지어내지 않고 못 찾았다고 말한다.
- 계산은 모델이 암산하지 않고 코드로 한다.
- 에이전트가 어떤 도구를 어떤 순서로 호출했는지 화면에 보여준다.
- 정답이 확인된 질문 세트로 정확도를 측정하고, 개선 과정을 수치로 기록한다.

## 진행 상황
- [x] 1단계: KOSIS API 직접 호출해보기 (`scripts/try_kosis.py`)
- [x] 2단계: 도구 4개 구현 (search / meta / data / calculate)
- [x] 3단계: Claude tool use 에이전트 루프
- [x] 4단계: eval 세트 + 첫 점수 (8/8, 출처 명시율 7/7)
- [ ] 5단계: 웹 화면 (FastAPI) + 배포 — 웹 화면은 로컬에서 동작 확인 완료, 배포는 미정
- [ ] 6단계: 개선 → 점수 변화 기록

## 시작하기

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# .env 파일을 열어 KOSIS_API_KEY 입력

python scripts/try_kosis.py              # 기본: '주민등록인구'
python scripts/try_kosis.py "고용률"

python scripts/ask.py "평택시 인구는 2022년에서 2023년 사이 얼마나 늘었어?"
python scripts/run_eval.py               # eval 세트 돌려서 점수 확인

uvicorn stat_agent.api:app --reload --app-dir src   # 웹 화면: http://localhost:8000
```

## 구조
```
stat-agent/
├── src/stat_agent/
│   ├── kosis_client.py   # KOSIS API 래퍼 (검색 / 메타 / 수치)
│   ├── tools.py          # 에이전트 도구 4개 (search/meta/data/calculate) + TOOL_SCHEMAS
│   ├── agent.py          # Claude tool-use 루프
│   └── api.py            # FastAPI 앱 (/api/ask)
├── web/                   # 순수 HTML/JS 웹 화면 (React 없음)
│   ├── index.html
│   └── static/ (style.css, app.js)
├── scripts/
│   ├── try_kosis.py      # 1단계 탐색 스크립트
│   ├── try_tools.py      # 2단계 도구 검증 스크립트
│   ├── ask.py            # 3단계 CLI (질문 → 답)
│   └── run_eval.py       # 4단계 eval 러너
├── .env.example
└── requirements.txt
```

## 참고
- 데이터 출처: 국가통계포털(KOSIS) 공유서비스 OpenAPI — https://kosis.kr/openapi
- 비슷한 프로젝트: [kosis-mcp](https://glama.ai/mcp/servers/updown256/kosis-mcp) (KOSIS를 MCP 서버로 감싼 도구).
  이 프로젝트는 에이전트 루프·도구 설계·정확도 평가를 직접 구현하는 데 초점을 둔다.

## 개발 노트
(진행하면서 부딪힌 문제와 해결 과정을 여기에 기록 — 면접에서 가장 많이 쓰이는 부분)

- **1단계**: Windows 콘솔(Git Bash)에서 한글이 깨져 나옴. `sys.stdout.encoding`이 `cp949`인데 터미널은 UTF-8을 기대해서 생긴 문제 — 로직 버그가 아니라 환경 문제였다. `sys.stdout.reconfigure(encoding="utf-8")`로 실행 환경과 무관하게 고정.
- **2단계**: `get_table_meta(type=ITM)`로 분류(지역 등) 코드를 받아보니 표 하나(주민등록인구)의 행정구역 코드가 4,819개였다. 모델에게 그대로 넘기면 토큰을 낭비하므로, `get_table_info` 도구에 `name_filter`를 추가해 코드 레이어에서 먼저 이름으로 좁히도록 설계. ("평택시" 검색 → 4,819개 중 1개로 좁혀짐, 코드=41220)
- **3단계**: `claude-haiku-5-5`로 에이전트 루프를 돌려보니 "평택시 인구는 최근 3년간 어떻게 변했어?" 질문에 대해 알맞은 표를 스스로 고르고(시군구/1세별 표), `name_filter`로 코드를 좁히고, `calculate_change`를 연도별로 4번 호출해 암산 없이 정확한 증감률을 계산했다. 저렴한 모델로도 이 정도 복잡도의 도구 체인은 충분히 처리됨 — 더 복잡한 질문(지역 비교, 모호한 키워드)에서 틀리면 Sonnet으로 올리는 걸 고려.
- **4단계**: 정답을 에이전트 자신이 아니라 `tools.py`를 직접 호출해 구한 값으로 미리 고정(2022~2024년처럼 과거 확정 연도 사용 — "최근"으로 물으면 다음 달 데이터 갱신 때마다 정답이 바뀜). 단순 조회·증감 계산·존재하지 않는 지역("삼성시") 질문 8개로 첫 점수 측정: **8/8 정답, 출처 명시율 7/7**. 존재하지 않는 지역 질문에서 지어내지 않고 "못 찾았다"고 답한 것 확인.
- **5단계**: 웹 화면에 "에이전트가 뭘 호출했는지 보여준다"는 요구사항을 만족시키려고, `run_agent`가 답변 문자열만 돌려주던 걸 `{"answer", "trace"}` 형태로 바꿨다. React 없이 순수 HTML/JS로 최소 구성 — 질문 하나에 보통 3~5번 도구를 호출하는데, 그 과정이 `<details>`로 접혀 있다가 펼쳐 보는 식이라 디버깅할 때도 바로 눈에 보여서 유용했다.
