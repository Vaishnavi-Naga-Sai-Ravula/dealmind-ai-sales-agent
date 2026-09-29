from backend.database.repository import Repository
from backend.memory.hindsight import HindsightMemory, MemoryUnavailable
from backend.models import Deal, Interaction


class DealService:
    def __init__(self, repository: Repository, memory: HindsightMemory):
        self.repository, self.memory = repository, memory

    async def retain(self, deal: Deal, interaction: Interaction) -> Interaction:
        try:
            await self.memory.retain(deal, interaction)
            interaction.memory_status, interaction.memory_error = 'retained', None
        except MemoryUnavailable as exc:
            interaction.memory_status, interaction.memory_error = 'failed', str(exc)
        self.repository.update_interaction(interaction)
        return interaction

    async def sync(self, deal: Deal) -> dict:
        # Oldest first: preserve the narrative when processing historical interactions.
        pending = sorted((i for i in deal.interactions if i.memory_status != 'retained'),
                         key=lambda i: i.occurred_at)
        retained = 0
        error = None
        for interaction in pending:
            result = await self.retain(deal, interaction)
            if result.memory_status == 'failed':
                error = result.memory_error
                break  # Do not repeat a failing external call for the entire history.
            retained += 1
        return {'retained': retained, 'remaining': len(pending) - retained, 'error': error}
