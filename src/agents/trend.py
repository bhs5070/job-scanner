import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import AgentState
from src.agents.utils import get_llm, render_prompt
from src.common.prompts import load_prompt
from src.db.crud.job_postings import get_posting_stats, get_tech_stack_counts
from src.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _build_trend_data(db) -> str:
    """Build trend data text from DB aggregation."""
    stats = get_posting_stats(db)
    tech_counts = get_tech_stack_counts(db)

    lines = [f"전체 활성 공고: {stats['total']}건"]
    for site, count in stats["by_site"].items():
        lines.append(f"  - {site}: {count}건")

    lines.append("\n## 기술 스택 빈도")
    if not tech_counts:
        lines.append("(기술 스택 데이터가 부족합니다)")
    else:
        for i, (tech, count) in enumerate(tech_counts, 1):
            pct = round(count / stats["total"] * 100, 1) if stats["total"] else 0
            lines.append(f"{i}. {tech}: {count}건 ({pct}%)")

    return "\n".join(lines)


def trend(state: AgentState) -> dict:
    """Analyze job posting trends using SQL aggregation."""
    llm = get_llm(temperature=0.3)

    db = SessionLocal()
    try:
        trend_data = _build_trend_data(db)

        prompt = render_prompt(
            load_prompt("trend_analysis"),
            trend_data=trend_data,
            user_input=state["user_input"],
        )

        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=state["user_input"]),
        ])
        return {"final_response": response.content}

    except Exception as e:
        logger.error(f"Trend agent failed: {e}")
        return {
            "final_response": "트렌드 분석 중 오류가 발생했습니다. 다시 시도해 주세요.",
            "error": str(e),
        }
    finally:
        db.close()
