from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: str
    stage: str
    revision_round: int = Field(alias="revisionRound")
    max_revision_rounds: int = Field(alias="maxRevisionRounds")
    best_score: float | None = Field(alias="bestScore")
    journal_id: str | None = Field(alias="journalId")
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
