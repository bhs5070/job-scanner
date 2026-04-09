# Job Scanner

**AI 채용 분석 에이전트 + LLM Evaluation 시스템**

채용 공고를 자동 수집하고, 7개 AI 에이전트가 공고 검색 / 이력서 매칭 / 역량 갭 분석 / 트렌드 분석 / 면접 준비를 대화형으로 제공합니다. 에이전트 답변 품질은 GPT-4o Judge로 10개 메트릭을 자동 평가하며, 프롬프트 튜닝을 통해 **평균 0.902**를 달성했습니다.

**Live Demo**: https://job-scanner-169081232409.asia-northeast3.run.app

---

## 주요 기능

### 1. AI 에이전트 대화 시스템

LangGraph StateGraph 기반 7개 에이전트가 사용자 의도를 자동 분류하고 처리합니다.

| 에이전트 | 기능 |
|---------|------|
| Router | 사용자 의도 분류 (LLM 기반, 6가지 카테고리) |
| Search | pgvector 벡터 유사도 검색으로 채용 공고 탐색 |
| Match | 이력서 PDF 텍스트 추출 후 공고 적합도 분석 |
| Gap | 목표 포지션까지 부족한 역량 분석 + 학습 로드맵 제안 |
| Trend | DB 집계 기반 기술 스택 트렌드 분석 |
| Interview | JD 기반 예상 면접 질문 생성 (기술 5개 + 인성 3개) |
| Chitchat | 일반 대화 및 서비스 안내 |

### 2. JD 자동 수집 파이프라인

원티드, 사람인에서 채용 공고를 자동 크롤링하고 PostgreSQL에 저장합니다.

- `BaseCrawler` 추상 클래스 + Registry 패턴으로 크롤러 확장 용이
- Airflow DAG 4개 (크롤링, 인덱싱, 평가, 만료 감지)
- 중복 제거 (`source_url` UNIQUE + ON CONFLICT upsert)
- 현재 473건 공고 수집 완료

### 3. 벡터 인덱싱 + RAG 검색

수집된 공고를 OpenAI `text-embedding-3-large`로 임베딩하여 pgvector에 인덱싱합니다.

- 섹션 기반 청킹 (full + requirements)
- Query Rewriting으로 대화체 → 검색 키워드 변환
- pgvector HNSW 인덱스 (1536차원, 코사인 유사도)
- 증분 인덱싱 (`indexed_at IS NULL` 기준)

### 4. LLM Evaluation 시스템

GPT-4o를 Judge 모델로 사용하여 에이전트 응답 품질을 10개 메트릭으로 자동 평가합니다.

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
| Routing Accuracy | 의도 분류 정확도 (GPT-4o 재분류) |
| Latency | 응답 시간 |

### 5. 웹 UI + 사용자 시스템

- Google OAuth2 로그인 (HMAC 서명 쿠키)
- 온보딩 프로필 (경력, 직군, 기술 스택 태그 선택, 학력, 희망 연봉/지역)
- 이력서/포트폴리오 PDF 드래그 앤 드롭 업로드 + 텍스트 추출 → 에이전트 컨텍스트 자동 주입
- 마이페이지: 내 정보, 경쟁력 대시보드, 관심 공고 북마크 (상태 관리), 매칭 기록
- 대화 히스토리 자동 저장 + 사이드바 이전 대화 목록
- 에이전트 응답 피드백 (엄지 업/다운)

---

## LLM Eval 결과

합성 쿼리 18건에 대해 GPT-4o Judge로 10개 메트릭을 자동 평가한 결과입니다. 프롬프트 튜닝과 데이터 확장을 통해 평균 **0.747 → 0.902** (+20.8%)로 개선했습니다.

| 메트릭 | 점수 |
|--------|------|
| Relevance | 0.944 |
| Groundedness | 0.889 |
| Helpfulness | 0.833 |
| Faithfulness | 0.889 |
| Answer Completeness | 0.944 |
| Retrieval Precision | 0.972 |
| Retrieval MRR | 0.972 |
| Context Relevance | 0.944 |
| Routing Accuracy | 0.722 |
| **평균** | **0.902** |

> 응답 생성: GPT-4o-mini (비용 효율), 평가: GPT-4o (엄격한 판정)으로 모델을 분리하여 평가 신뢰도를 확보했습니다.
> 개선 과정 상세: [docs/eval-improvement.md](docs/eval-improvement.md)

---

## 아키텍처

```
사용자 (브라우저)
    |
FastAPI Gateway (/api/*)
    |
    ├── /api/chat → LangGraph Agent System (7 agents)
    │                ├── Router Agent (의도 분류, 6 categories)
    │                ├── Search / Match / Gap / Interview Agent → pgvector (벡터 검색)
    │                ├── Trend Agent → PostgreSQL (SQL 집계)
    │                └── Chitchat Agent
    │
    ├── /api/auth      → Google OAuth2 (HMAC signed cookie)
    ├── /api/profile   → 프로필 CRUD + PDF 업로드 (DB 영속)
    ├── /api/bookmarks → 관심 공고 북마크 + 상태 관리
    ├── /api/history   → 매칭 기록 자동 저장
    ├── /api/feedback  → 응답 피드백 (엄지 업/다운)
    ├── /api/eval      → Eval 결과 조회
    └── /api/dashboard → 경쟁력 분석

Airflow DAGs (BashOperator — SQLAlchemy 충돌 회피)
    ├── jd_crawling      (매일 09:00 KST) → 원티드 + 사람인 크롤링
    ├── jd_indexing       (매일 10:00 KST) → pgvector 임베딩
    ├── llm_eval          (매일 12:00 KST) → GPT-4o Judge 평가
    └── jd_expiry_check   (매주 일요일)    → 만료 공고 감지

Deployment
    ├── GCP Cloud Run (서버)
    └── Neon PostgreSQL + pgvector (DB + 벡터 검색)
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Database | PostgreSQL 16 (Neon), SQLAlchemy 2.0, Alembic, pgvector |
| Agent | LangGraph (StateGraph), LangChain |
| LLM | OpenAI GPT-4o-mini (응답), GPT-4o (평가) |
| Embedding | text-embedding-3-large (1536dim) → pgvector HNSW |
| Eval | LLM-as-Judge (10 metrics), MLflow |
| Pipeline | Apache Airflow (BashOperator) |
| Auth | Google OAuth2, HMAC-SHA256 signed cookies |
| Deploy | GCP Cloud Run, Docker, Neon PostgreSQL |
| Frontend | Vanilla JS, marked.js, DOMPurify |

---

## 프로젝트 구조

```
src/
├── api/            ← FastAPI Gateway
│   ├── main.py
│   ├── deps.py     (의존성 주입 — 인증, DB 세션, 그래프)
│   └── routers/    (auth, chat, profile, bookmarks, history,
│                    dashboard, eval, feedback, conversations)
├── agents/         ← LangGraph Agent System
│   ├── state.py    (AgentState TypedDict)
│   ├── graph.py    (StateGraph 조립 — 7 nodes)
│   ├── router.py   (의도 분류 — 18 few-shot examples)
│   ├── search.py   (Query Rewriting + pgvector 검색)
│   ├── match.py    (이력서 매칭 분석)
│   ├── gap.py      (역량 갭 + 학습 로드맵)
│   ├── trend.py    (SQL 집계 → LLM 해석)
│   ├── interview.py(면접 질문 생성)
│   ├── chitchat.py (일반 대화)
│   ├── respond.py  (대화 이력 관리)
│   └── utils.py    (LLM 캐싱, 검색 결과 포맷)
├── eval/           ← LLM Evaluation
│   ├── metrics/judge.py  (GPT-4o Judge — 10 metrics)
│   └── pipeline.py       (배치 평가 + MLflow 연동)
├── crawlers/       ← JD 크롤링
│   ├── base.py     (BaseCrawler ABC)
│   ├── registry.py (크롤러 레지스트리)
│   └── sites/      (wanted, saramin, rocketpunch)
├── indexing/       ← 벡터 인덱싱
│   ├── chunker.py  (섹션 기반 청킹)
│   ├── indexer.py  (pgvector upsert)
│   ├── retriever.py(코사인 유사도 검색)
│   └── pipeline.py (증분 인덱싱 파이프라인)
├── db/             ← Database
│   ├── models.py   (10 tables)
│   ├── crud/       (job_postings, crawl_logs)
│   ├── base.py
│   └── session.py
└── common/
    ├── config.py   (pydantic-settings)
    └── prompts/    (12 프롬프트 .txt 파일)

pipelines/dags/     ← Airflow DAGs (4개)
scripts/            ← 파이프라인 수동 실행 스크립트
frontend/           ← Web UI (HTML/CSS/JS)
docs/               ← 설계 문서, Eval 개선 기록
```

---

## 시작하기

### 사전 요구사항

- Python 3.11+
- PostgreSQL 15+ (또는 Neon)
- OpenAI API Key
- Google OAuth Client ID/Secret (로그인 기능용)

### 설치

```bash
git clone https://github.com/bhs5070/job-scanner.git
cd job-scanner

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env에 OPENAI_API_KEY, DATABASE_URL, GOOGLE_CLIENT_ID 등 설정

createdb job_scanner
PYTHONPATH=. alembic upgrade head
```

### 실행

```bash
PYTHONPATH=. uvicorn src.api.main:app --port 8000
open http://localhost:8000
```

### 파이프라인 실행

```bash
./scripts/run_pipeline.sh crawl   # 크롤링
./scripts/run_pipeline.sh index   # 벡터 인덱싱
./scripts/run_pipeline.sh eval    # LLM 평가
./scripts/run_pipeline.sh all     # 전부 실행
```

### Airflow 실행 (Docker)

```bash
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
docker compose -f docker-compose.airflow.yml up -d

# Airflow UI: http://localhost:8081 (admin / admin)
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

역방향 import 금지. 이 규칙을 지켜 향후 서비스 분리가 가능한 Modular Monolith 구조.

---

## 라이선스

MIT
