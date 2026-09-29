from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class DealCreate(InputModel):
    company: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=1, max_length=120)
    role: str = Field(default='', max_length=120)
    industry: str = Field(default='', max_length=120)
    title: str = Field(min_length=1, max_length=200)
    stage: Literal['Discovery', 'Evaluation', 'Proposal', 'Negotiation', 'Won', 'Lost'] = 'Discovery'
    value: float = Field(default=0, ge=0, le=1_000_000_000, allow_inf_nan=False)
    summary: str = Field(default='', max_length=4000)


class InteractionCreate(InputModel):
    channel: Literal['Call', 'Email', 'Meeting', 'Note'] = 'Call'
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=3, max_length=12000)
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Interaction(InteractionCreate):
    id: str
    deal_id: str
    memory_status: Literal['pending', 'retained', 'failed'] = 'pending'
    memory_error: str | None = None


class Deal(DealCreate):
    id: str
    created_at: str
    interactions: list[Interaction] = Field(default_factory=list)


class Memory(BaseModel):
    id: str
    text: str
    type: str = 'world'
    document_id: str | None = None


class RecallRequest(InputModel):
    query: str = Field(default='Previous concerns, objections, requirements, preferences and next steps', min_length=3, max_length=2000)


class RecallResult(BaseModel):
    provider: str = 'hindsight'
    bank_id: str
    query: str
    memories: list[Memory]


class IntelligenceResult(BaseModel):
    mode: Literal['hindsight', 'demo']
    brief: str
    next_actions: list[str]
    memories: list[Memory]
    warning: str | None = None
    generated_at: str
