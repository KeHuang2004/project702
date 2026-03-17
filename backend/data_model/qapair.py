from typing import Any, Dict, Tuple

from utils.database__manager.base_model import BaseModel


class QApair(BaseModel):
    """QApair 数据模型：最小实体为问答对"""

    def __init__(self, question: str = "", answer: str = ""):
        super().__init__()
        self.question: str = question
        self.answer: str = answer

    @classmethod
    def get_table_name(cls) -> str:
        return "qapairs"

    @classmethod
    def from_row(cls, row) -> "QApair":
        obj = cls()
        obj.id = row["id"] if "id" in row.keys() else row[0]
        obj.question = row["question"] if "question" in row.keys() else row[1]
        obj.answer = row["answer"] if "answer" in row.keys() else row[2]
        return obj

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QApair":
        obj = cls(
            question=str(data.get("question", "")),
            answer=str(data.get("answer", "")),
        )
        obj.id = data.get("id")
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
        }

    def get_insert_fields(self) -> Tuple[str, tuple]:
        fields = "question, answer"
        values = (self.question, self.answer)
        return fields, values

    def get_update_fields(self) -> Tuple[str, tuple]:
        set_clause = "question = ?, answer = ?"
        values = (self.question, self.answer)
        return set_clause, values
