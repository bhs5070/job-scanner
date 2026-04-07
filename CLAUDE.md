# Job Scanner — Project Instructions

## Overview

AI 채용 분석 에이전트 + LLM Evaluation 시스템.
JD(채용공고)를 자동 수집 → 분석 → 이력서 매칭 → 트렌드 리포트를 제공하고,
에이전트 답변 품질을 자동으로 평가/모니터링하는 프로젝트.

## Architecture

- **아키텍처 패턴**: Modular Monolith (개발) → 부분 서비스 분리 (배포)
- **상세 설계**: `Desktop/job-scanner-아키텍처.md` 참조

## Tech Stack

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Database | PostgreSQL 15, SQLAlchemy 2.0, Alembic |
| Agent | LangGraph, LangChain |
| Vector DB | ChromaDB |
| LLM | OpenAI (GPT-4o-mini, text-embedding-3-large) |
| Eval | LLM-as-Judge, MLflow |
| Observability | LangSmith |
| Pipeline | Apache Airflow |
| Frontend | HTML/CSS/Vanilla JS |

## Project Structure

```
src/
├── api/          ← FastAPI Gateway
├── agents/       ← LangGraph Agent System
├── eval/         ← LLM Evaluation
├── crawlers/     ← JD Crawling
├── db/           ← Database (models, CRUD, migrations)
├── indexing/     ← Vector Embedding & Indexing
└── common/       ← Config, Prompts, Utils
pipelines/        ← Airflow DAGs
tests/            ← Test code
frontend/         ← Web UI
```

## Module Dependency Rules

```
api/ → agents/, db/
agents/ → db/, indexing/, common/
eval/ → db/, common/
crawlers/ → db/, common/
pipelines/ → crawlers/, indexing/, eval/
indexing/ → common/
db/ → common/
common/ → 없음 (최하위 계층)
```

역방향 import 절대 금지. 이 규칙을 지켜야 나중에 서비스 분리가 가능함.

## Code Conventions

### Python
- Python 3.11+
- PEP 8 준수
- Import 순서: 표준 라이브러리 → 서드파티 → 로컬
- Import 경로: 절대 경로 사용 (`from src.agents import ...`)
- Type hints 필수 (함수 파라미터, 리턴 타입)
- Docstring: 복잡한 함수에만 간결하게

### FastAPI
- Router별 파일 분리 (`src/api/routers/`)
- Pydantic v2 모델로 요청/응답 스키마 정의
- 의존성 주입은 `src/api/deps.py`에서 관리

### Database
- SQLAlchemy 2.0 스타일 (declarative_base)
- 마이그레이션은 Alembic으로 관리
- CRUD 함수는 `src/db/crud/` 테이블별 분리

### LangGraph
- State 정의: `src/agents/state.py`
- Agent별 파일 분리 (하나의 Agent = 하나의 파일)
- 그래프 조립: `src/agents/graph.py`

### Prompts
- 모든 프롬프트 템플릿은 `src/common/prompts/`에서 관리
- 하드코딩 금지, 반드시 파일로 분리

### Testing
- pytest 사용
- 테스트 파일은 `tests/` 하위에 모듈 구조 미러링

## Workflow

이 프로젝트는 하네스 엔지니어링으로 진행됨:
1. Product Strategist → 요구사항 정리
2. Plan (Architect) → 설계
3. Fullstack Developer / RAG Pipeline Engineer → 구현
4. Code Reviewer → 리뷰
5. 사용자 (하네스) → 최종 확인 + 머지

## Communication

- 한국어로 소통
- 코드 주석은 영어 또는 한국어 (일관성 유지)
- 커밋 메시지는 영어 (conventional commits: feat, fix, refactor, docs, test)
