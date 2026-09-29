from fastapi import APIRouter, HTTPException, Request

from backend.models import (Deal, DealCreate, Interaction, InteractionCreate,
                            IntelligenceResult, RecallRequest, RecallResult)

router = APIRouter(prefix='/api')


def get_deal(request: Request, deal_id: str) -> Deal:
    deal = request.app.state.repository.get_deal(deal_id)
    if deal is None:
        raise HTTPException(404, 'Deal not found')
    return deal


@router.get('/health')
def health(request: Request):
    settings = request.app.state.settings
    return {'status': 'ok', 'memory_provider': 'hindsight',
            'memory_configured': bool(settings.hindsight_base_url),
            'intelligence_mode': settings.intelligence_mode,
            'note': 'Configuration status only; use recall or sync to verify the external service.'}


@router.get('/deals', response_model=list[Deal])
def list_deals(request: Request):
    return request.app.state.repository.list_deals()


@router.post('/deals', response_model=Deal, status_code=201)
def create_deal(data: DealCreate, request: Request):
    return request.app.state.repository.create_deal(data)


@router.get('/deals/{deal_id}', response_model=Deal)
def deal_detail(deal_id: str, request: Request):
    return get_deal(request, deal_id)


@router.post('/deals/{deal_id}/interactions', response_model=Interaction, status_code=201)
async def create_interaction(deal_id: str, data: InteractionCreate, request: Request):
    deal = get_deal(request, deal_id)
    interaction = request.app.state.repository.add_interaction(deal_id, data)
    # A 201 means the CRM record was saved. memory_status reports external delivery separately.
    return await request.app.state.deals.retain(deal, interaction)


@router.post('/deals/{deal_id}/memory/sync')
async def sync_memory(deal_id: str, request: Request):
    return await request.app.state.deals.sync(get_deal(request, deal_id))


@router.post('/deals/{deal_id}/memory/recall', response_model=RecallResult)
async def recall_memory(deal_id: str, data: RecallRequest, request: Request):
    deal = get_deal(request, deal_id)
    memory = request.app.state.memory
    return RecallResult(bank_id=memory.bank_id(deal_id), query=data.query,
                        memories=await memory.recall(deal, data.query))


@router.post('/deals/{deal_id}/intelligence', response_model=IntelligenceResult)
async def intelligence(deal_id: str, data: RecallRequest, request: Request):
    return await request.app.state.intelligence.generate(get_deal(request, deal_id), data.query)
