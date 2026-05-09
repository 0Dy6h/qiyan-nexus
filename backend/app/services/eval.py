from pathlib import Path

from app.schemas.eval import load_rag_eval_dataset


_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "evals" / "rag_ad_eval_questions.json"


def get_rag_eval_questions() -> list[dict]:
    return [item.dict() for item in load_rag_eval_dataset(_DATA_PATH)]
