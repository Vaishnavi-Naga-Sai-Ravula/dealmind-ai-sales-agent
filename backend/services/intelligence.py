from datetime import datetime, timezone

from backend.agents.sales import demo_brief, suggested_actions
from backend.memory.hindsight import MemoryUnavailable
from backend.models import Deal, IntelligenceResult


class IntelligenceService:
    def __init__(self, memory, mode: str):
        self.memory, self.mode = memory, mode

    async def generate(self, deal: Deal, query: str) -> IntelligenceResult:
        memories, warning = [], None
        mode = self.mode
        try:
            memories = await self.memory.recall(deal, query)
        except MemoryUnavailable as exc:
            warning = str(exc)
            mode = 'demo'
        if mode == 'hindsight' and not memories:
            mode = 'demo'
            warning = 'No Hindsight memories were returned. Sync interactions or try a broader query.'
        if mode == 'hindsight':
            try:
                brief = await self.memory.reflect(deal, query, memories)
            except MemoryUnavailable as exc:
                mode, warning = 'demo', str(exc)
        if mode == 'demo':
            brief = demo_brief(deal, memories)
            warning = (warning + ' ' if warning else '') + 'Rules-based development brief; not AI-generated.'
        return IntelligenceResult(mode=mode, brief=brief, memories=memories,
                                  next_actions=suggested_actions(deal, memories), warning=warning,
                                  generated_at=datetime.now(timezone.utc).isoformat())
