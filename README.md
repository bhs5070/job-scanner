# Job Scanner

AI 채용 분석 에이전트 + LLM Evaluation 시스템

채용 공고를 자동 수집하고, AI 에이전트가 공고 검색 / 이력서 매칭 / 역량 갭 분석 / 트렌드 분석을 대화형으로 제공합니다. 에이전트 답변 품질은 LLM-as-Judge 방식으로 10개 메트릭을 자동 평가합니다.

---

## 주요 기능

### 1. AI 에이전트 대화 시스템
LangGraph StateGraph 기반 6개 에이전트가 사용자 의도를 자동 분류하고 처리합니다.

| 에이전트 | 기능 |
|---------|------|
| Router | 사용자 의도 분류 (LLM 기반, 5가지 카테고리) |
| Search | 벡터 유사도 검색으로 채용 공고 탐색 |
| Match | 이력서 PDF 텍스트 추출 후 공고 적합도 분석 |
| Gap | 목표 포지션까지 부족한 역량 분석 + 학습 경로 제안 |
| Trend | DB 집계 기반 기술 스택 트렌드 분석 |
| Chitchat | 일반 대화 및 서비스 안내 |

### 2. JD 자동 수집 파이프라인
원티드, 사람인에서 채용 공고를 자동 크롤링하고 PostgreSQL에 저장합니다.

- `BaseCrawler` 추상 클래스 + Registry 패턴으로 크롤러 확장 용이
- Airflow DAG으로 매일 자동 실행
- 중복 제거 (source_url UNIQUE)

### 3. 벡터 인덱싱 + RAG 검색
수집된 공고를 OpenAI `text-embedding-3-large`로 임베딩하여 ChromaDB에 인덱싱합니다.

- 섹션 기반 청킹 (full + requirements)
- Query Rewriting으로 검색 정밀도 향상
- 증분 인덱싱 (indexed_at IS NULL 기준)

### 4. LLM Evaluation 시스템
GPT-4o를 Judge 모델로 사용하여 에이전트 응답 품질을 자동 평가합니다.

| 메트릭 | 설명 |
|--------|------|
| Relevance | 질문-답변 관련성 |
| Groundedness | 데이터 근거 여부 |
| Helpfulness | 취업 준비생에게 실용성 |
| Faithfulness | Hallucination 검증 |
| Answer Completeness | 답변 완전성 |
| Retrieval Precision | 검색 정밀도 |
| Retrieval MRR | 검색 순위 품질 |
| Context Relevance | 컨텍스트 적합성 |
| Routing Accuracy | 라우터 분류 정확도 |
| Latency | 응답 시간 |

### 5. 웹 UI + 사용자 시스템
- Google OAuth 로그인
- 프로필 설정 (경력, 직군, 기술 스택 태그 선택, 학력)
- 이력서/포트폴리오 PDF 업로드 + 텍스트 추출 → 에이전트 컨텍스트 자동 주입
- 마이페이지: 내 정보, 경쟁력 대시보드, 관심 공고 북마크, 매칭 기록

---

## 아키텍처

```
사용자 (브라우저)
    |
FastAPI Gateway (/api/*)
    |
    ├── /api/chat → LangGraph Agent System
    │                ├── Router Agent (의도 분류)
    │                ├── Search / Match / Gap Agent → ChromaDB (벡터 검색)
    │                ├── Trend Agent → PostgreSQL (SQL 집계)
    │                └── Chitchat Agent
    │
    ├── /api/auth → Google OAuth2
    ├── /api/profile → 프로필 CRUD + 파일 업로드
    ├── /api/bookmarks → 관심 공고 북마크
    ├── /api/eval → 평가 결과 조회
    └── /api/dashboard → 경쟁력 분석

Airflow DAGs
    ├── jd_crawling  (매일 09:00 KST) → 크롤러 → PostgreSQL
    ├── jd_indexing  (매일 10:00 KST) → 임베딩 → ChromaDB
    └── llm_eval     (매일 12:00 KST) → GPT-4o Judge → eval_results
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Database | PostgreSQL 15, SQLAlchemy 2.0, Alembic |
| Agent | LangGraph, LangChain |
| LLM | OpenAI GPT-4o-mini (응답), GPT-4o (평가) |
| Vector DB | ChromaDB, text-embedding-3-large |
| Eval | LLM-as-Judge (10 metrics), MLflow |
| Pipeline | Apache Airflow |
| Auth | Google OAuth2, HMAC signed cookies |
| Frontend | HTML/CSS/Vanilla JS, marked.js, DOMPurify |

---

## 프로젝트 구조

```
src/
├── api/            ← FastAPI Gateway + 라우터
│   ├── main.py
│   ├── deps.py
│   └── routers/    (auth, chat, profile, bookmarks, history, dashboard, eval, conversations)
├── agents/         ← LangGraph Agent System
│   ├── state.py    (AgentState TypedDict)
│   ├── graph.py    (StateGraph 조립)
│   ├── router.py   (의도 분류)
│   ├── search.py   (벡터 검색)
│   ├── match.py    (이력서 매칭)
│   ├── gap.py      (역량 갭 분석)
│   ├── trend.py    (트렌드 집계)
│   ├── chitchat.py (일반 대화)
│   └── utils.py    (LLM 캐싱, 유틸)
├── eval/           ← LLM Evaluation
│   ├── metrics/judge.py  (LLM-as-Judge, 10 metrics)
│   └── pipeline.py       (배치 평가 파이프라인)
├── crawlers/       ← JD 크롤링
│   ├── base.py     (BaseCrawler ABC)
│   ├── registry.py
│   └── sites/      (wanted, saramin, rocketpunch)
├── indexing/       ← 벡터 인덱싱
│   ├── chunker.py  (섹션 기반 청킹)
│   ├── embedder.py (OpenAI 임베딩)
│   ├── indexer.py  (ChromaDB upsert)
│   └── retriever.py(유사도 검색)
├── db/             ← Database
│   ├── models.py   (8 tables)
│   ├── crud/
│   └── session.py
└── common/
    ├── config.py   (pydantic-settings)
    └── prompts/    (10+ 프롬프트 .txt 파일)

pipelines/dags/     ← Airflow DAGs (crawling, indexing, eval)
frontend/           ← Web UI (HTML/CSS/JS)
```

---

## 시작하기

### 사전 요구사항

- Python 3.11+
- PostgreSQL 15
- OpenAI API Key

### 설치

```bash
git clone https://github.com/bhs5070/job-scanner.git
cd job-scanner

# 가상환경
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 환경변수
cp .env.example .env
# .env 파일에 OPENAI_API_KEY, DATABASE_URL 등 설정

# DB 생성 + 마이그레이션
createdb job_scanner
PYTHONPATH=. alembic upgrade head
```

### 실행

```bash
# 서버 실행
PYTHONPATH=. uvicorn src.api.main:app --port 8000

# 브라우저에서 접속
open http://localhost:8000
```

### 데이터 수집 (수동)

```bash
# 크롤링
PYTHONPATH=. python -c "
from src.crawlers import run_crawl_job
from src.db.crud.job_postings import bulk_upsert_job_postings
from src.db.session import SessionLocal
db = SessionLocal()
for site in ['wanted', 'saramin']:
    result = run_crawl_job(site=site, keywords=['AI Engineer', 'ML Engineer'], max_pages=2)
    rows = [{'source_site': i.source_site, 'source_url': i.source_url, 'title': i.title,
             'company': i.company, 'description': i.description, 'requirements': i.requirements,
             'tech_stack': i.tech_stack, 'collected_at': i.collected_at} for i in result.items]
    bulk_upsert_job_postings(db, rows)
    print(f'{site}: {result.total_parsed}건')
db.close()
"

# 벡터 인덱싱
PYTHONPATH=. python -c "
from src.db.session import SessionLocal
from src.indexing.pipeline import run_incremental_index
db = SessionLocal()
print(run_incremental_index(db))
db.close()
"
```

---

## 모듈 의존성 규칙

```
api/ → agents/, db/
agents/ → db/, indexing/, common/
eval/ → db/, common/
crawlers/ → db/, common/
pipelines/ → crawlers/, indexing/, eval/
indexing/ → common/
db/ → common/
common/ → (없음)
```

역방향 import 금지.

---

## 라이선스

MIT
