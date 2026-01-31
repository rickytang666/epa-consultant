"""api endpoints"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from api.schemas import QueryRequest, QueryResponse, TableResponse
from ml.rag_pipeline import query_rag

router = APIRouter(prefix='/api')

@router.get("/status")
async def status():
    return {"status": "ok"}

@router.post("/query")
async def query(request: QueryRequest):
    """
    query endpoint - receives question and streams answer
    
    uses server-sent events for streaming
    """
    async def generate():
        async for chunk in query_rag(request.question):
            if chunk["type"] == "content":
                yield f"content: {chunk['delta']}\n\n"
            elif chunk["type"] == "sources":
                yield f"sources: {json.dumps(chunk['data'])}\n\n"
        yield "state: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/tables")
async def get_tables() -> TableResponse:
    """
    get all extracted tables
    
    returns:
        list of tables with structured data
    """
    # TODO: load tables from data/processed/tables.json
    return TableResponse(tables=[])
