import asyncio
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.feat.pipeline import run_analysis_pipeline
from src.feat.search_router import search_router
from src.models.pipeline import AnalyzeRequest, PipelineResult, RoutingStrategy

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"name": "consumer-signal-ai", "status": "ok"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


@app.post("/analyze", response_model=PipelineResult)
async def analyze_product(payload: AnalyzeRequest):
    return await run_analysis_pipeline(payload)


@app.post("/analyze/stream")
async def analyze_product_stream(payload: AnalyzeRequest):
    async def event_generator():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def emit_progress(event: dict):
            await queue.put(event)

        async def runner():
            try:
                result = await run_analysis_pipeline(
                    payload,
                    progress_callback=emit_progress,
                )
                await queue.put(
                    {
                        "type": "result",
                        "data": result.model_dump(),
                    }
                )
            except Exception as exc:
                await queue.put(
                    {
                        "type": "error",
                        "message": str(exc),
                    }
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(runner())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield json.dumps(item, ensure_ascii=False) + "\n"
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    import contextlib

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
