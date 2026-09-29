from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import ROOT, Settings
from backend.database.repository import Repository
from backend.memory.hindsight import HindsightMemory, MemoryUnavailable
from backend.routes import router
from backend.services.deals import DealService
from backend.services.intelligence import IntelligenceService


def create_app(settings: Settings | None = None, memory=None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository = Repository(settings.database_path)
        repository.initialize(ROOT / 'data/sample_deals.json' if settings.seed_sample_data else None)
        memory_layer = memory if memory is not None else HindsightMemory(settings)
        app.state.settings = settings
        app.state.repository = repository
        app.state.memory = memory_layer
        app.state.deals = DealService(repository, memory_layer)
        app.state.intelligence = IntelligenceService(memory_layer, settings.intelligence_mode)
        try:
            yield
        finally:
            await memory_layer.close()

    app = FastAPI(title='DealMind API', version='1.0.0', lifespan=lifespan,
                  description='Sales records → Hindsight retain → recall → sales briefing.')
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.exception_handler(MemoryUnavailable)
    async def memory_error(request: Request, exc: MemoryUnavailable):
        return JSONResponse(status_code=503, content={'detail': str(exc)})

    app.include_router(router)
    return app


app = create_app()
