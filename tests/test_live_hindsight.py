"""Opt in with RUN_LIVE_HINDSIGHT=1. Creates one uniquely named real memory bank."""
import asyncio
import os
from uuid import uuid4

import pytest

from backend.config import Settings
from backend.memory.hindsight import HindsightMemory
from backend.models import Deal, Interaction


@pytest.mark.live
@pytest.mark.skipif(os.getenv('RUN_LIVE_HINDSIGHT') != '1', reason='Live service test requires explicit opt-in')
def test_live_retain_recall_reflect():
    settings = Settings()
    assert settings.hindsight_base_url, 'Set HINDSIGHT_BASE_URL and the service API key if required.'
    deal = Deal(id=f'smoke-{uuid4().hex[:10]}', company='Fictional Smoke Co', contact='Alex',
                title='Residency pilot', created_at='2026-09-29T00:00:00Z')
    interaction = Interaction(id='residency-note', deal_id=deal.id, title='Discovery',
                              content='Alex requires India-only data residency before approving the pilot.')

    async def run():
        memory = HindsightMemory(settings)
        print(f'Live test bank (retained for inspection): {memory.bank_id(deal.id)}')
        try:
            await memory.retain(deal, interaction)
            recalled = await memory.recall(deal, 'What does Alex require before approving the pilot?')
            assert recalled, 'Retention completed but recall returned no evidence'
            assert any('india' in m.text.lower() for m in recalled)
            assert await memory.reflect(deal, 'What should we confirm before the pilot?', recalled)
        finally:
            await memory.close()

    asyncio.run(run())
