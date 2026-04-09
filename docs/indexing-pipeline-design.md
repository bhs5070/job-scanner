# JD 벡터 인덱싱 파이프라인 설계

## 1. 개요

JD(채용공고) 데이터를 ChromaDB에 벡터 인덱싱하여 의미 기반 검색을 지원하는 파이프라인.
PostgreSQL에 저장된 JD를 소스로, OpenAI text-embedding-3-large로 임베딩 생성 후 ChromaDB에 저장.

---

## 2. 파일 구조

```
src/indexing/
├── __init__.py
├── embedder.py          # OpenAI 임베딩 클라이언트 래퍼
├── chunker.py           # JD 청킹 전략
├── indexer.py           # ChromaDB 인덱싱 (write/delete)
├── retriever.py         # ChromaDB 검색 (read)
└── incremental.py       # 증분 인덱싱 추적 로직
```

---

## 3. ChromaDB Collection 설계

### Collection 이름: `job_scanner_jds`

### Document 구조 (청크 단위)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | `{job_id}_{chunk_type}` (예: `job_123_requirements`) |
| `document` | string | 임베딩 대상 텍스트 (청크 내용) |
| `embedding` | vector | text-embedding-3-large 결과 (3072차원) |
| `metadata` | dict | 아래 참고 |

### Metadata 필드

```python
{
    "job_id": int,          # PostgreSQL jobs 테이블 PK
    "chunk_type": str,      # "overview" | "requirements" | "preferred" | "benefits"
    "company": str,
    "title": str,
    "location": str,
    "job_type": str,        # "full_time" | "contract" | "intern"
    "source": str,          # "wanted" | "jumpit" | "saramin"
    "posted_date": str,     # ISO 8601
    "url": str,
    "indexed_at": str,      # ISO 8601, 인덱싱 시각
}
```

---

## 4. 청킹 전략

### 섹션 기반 청킹 (Section-based Chunking)

JD는 구조화된 텍스트이므로 의미 단위(섹션)로 분리.

```
[overview]    = title + company + 주요업무 요약
[requirements] = 자격요건 (필수)  ← 매칭에 가장 중요
[preferred]   = 우대사항
[benefits]    = 복지/혜택
```

**이유:**
- 전체 JD를 하나로 임베딩 → 요구사항 신호가 희석됨
- 검색 시 쿼리 의도에 맞는 섹션만 retrieve 가능
- 이력서 매칭 시 `requirements` 청크 위주로 검색

### 청크 크기 제한
- 섹션별 최대 1,500 tokens (text-embedding-3-large 한계 8,191 tokens 내)
- 초과 시 문단 단위로 추가 분할 (overlap 없음, 섹션 의미 유지)

### Fallback
- 섹션 구분 불가한 JD → 전체 텍스트를 `overview` 단일 청크로 처리

---

## 5. 임베딩 전략

### 모델
- `text-embedding-3-large` (3072차원)
- 비용 절감 시 `text-embedding-3-small` (1536차원)으로 교체 가능하도록 추상화

### 배치 처리
- OpenAI API 배치 제한: 2,048 입력/요청
- 내부적으로 100개 청크 단위 배치 처리
- Rate limit 대응: 지수 백오프 재시도 (3회)

### 임베딩 전처리
```python
# 청크 텍스트 정규화
text = f"[{chunk_type}]\n{content}"  # 섹션 타입 prefix 추가
text = re.sub(r'\s+', ' ', text).strip()
```

---

## 6. 증분 인덱싱 (Incremental Indexing)

### 전략: DB 기반 상태 추적

`jobs` 테이블에 인덱싱 상태 컬럼 추가:
```sql
ALTER TABLE jobs ADD COLUMN indexed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN index_status VARCHAR(20) DEFAULT 'pending';
-- index_status: 'pending' | 'indexed' | 'failed'
```

### 인덱싱 흐름

```
1. SELECT jobs WHERE index_status = 'pending' LIMIT 100
2. 청킹 → 임베딩 생성 → ChromaDB upsert
3. UPDATE jobs SET index_status='indexed', indexed_at=NOW() WHERE id=?
4. 실패 시 index_status='failed' 기록 (재시도 대상)
```

### Upsert 전략
- ChromaDB `collection.upsert()` 사용 → 동일 ID면 덮어쓰기
- JD 수정 시: 기존 청크 삭제 후 재인덱싱 (`index_status='pending'`으로 리셋)

---

## 7. Airflow DAG 연동

### DAG 구조

```
jd_pipeline_dag
├── crawl_task          (crawlers/)
│   └── >> index_task
└── index_task          (indexing/)
    ├── fetch_pending_jds()
    ├── chunk_and_embed()
    └── upsert_to_chromadb()
```

### DAG 트리거 방식
- `crawl_task` 완료 후 자동 실행 (task dependency)
- 독립 실행도 가능 (증분 처리이므로 안전)
- 스케줄: 매일 오전 2시 (`0 2 * * *`)

### 실패 처리
- `index_status='failed'`인 JD는 다음 실행 주기에 자동 재시도
- 연속 3회 실패 시 알림 (Airflow alert)

---

## 8. 핵심 인터페이스

### `src/indexing/indexer.py`

```python
class JDIndexer:
    def __init__(self, chroma_client: chromadb.Client, embedder: JDEmbedder) -> None: ...
    
    def index_jobs(self, jobs: list[JobRecord]) -> IndexResult: ...
    def delete_job(self, job_id: int) -> None: ...
    def reindex_job(self, job_id: int) -> IndexResult: ...
```

### `src/indexing/retriever.py`

```python
class JDRetriever:
    def __init__(self, chroma_client: chromadb.Client, embedder: JDEmbedder) -> None: ...
    
    def search(
        self,
        query: str,
        chunk_types: list[str] | None = None,  # 필터링
        n_results: int = 10,
        where: dict | None = None,              # metadata 필터
    ) -> list[SearchResult]: ...
```

### `src/indexing/chunker.py`

```python
class JDChunker:
    def chunk(self, job: JobRecord) -> list[JDChunk]: ...
```

---

## 9. 의존성

```
src/indexing/ → src/common/ (config, utils)
```
- DB 직접 접근 없음. `jobs` 레코드는 호출자(Airflow task/API)가 넘겨줌
- 모듈 독립성 유지 → 서비스 분리 용이

---

## 10. 주요 설계 결정 사항

| 결정 | 이유 |
|------|------|
| 섹션 기반 청킹 | JD 구조 활용, requirements 신호 강화, 검색 정밀도 향상 |
| `job_id_chunk_type` ID 포맷 | 청크 추적 용이, upsert 시 중복 방지 |
| DB 컬럼 기반 상태 추적 | 별도 상태 테이블 불필요, 트랜잭션 안전성 확보 |
| 임베딩 레이어 추상화 | 모델 교체 시 indexer/retriever 코드 변경 최소화 |
| Retriever 분리 | agents/가 indexing/에 의존하되, 읽기/쓰기 책임 분리 |
