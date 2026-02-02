"""api endpoints"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from pathlib import Path
from api.schemas import QueryRequest, QueryResponse, TableResponse
from ml.rag_pipeline import query_rag

router = APIRouter(prefix="/api")


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
        accumulated_response = []
        sources_count = 0

        async for chunk in query_rag(request.question):
            if chunk["type"] == "content":
                # print(chunk)
                accumulated_response.append(chunk["delta"])
                yield f"content: {json.dumps(chunk['delta'])}\n\n"
            elif chunk["type"] == "sources":
                sources_count = len(chunk["data"])
                yield f"sources: {json.dumps(chunk['data'])}\n\n"

        # Print complete response to terminal
        if accumulated_response:
            full_response = "".join(accumulated_response)
            print(f"\n{'=' * 80}\nQUESTION: {request.question}\n{'=' * 80}")
            print(full_response)
            print(f"\n[Sources: {sources_count} chunks]\n{'=' * 80}\n")

        yield "state: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/tables")
async def get_tables() -> TableResponse:
    """
    get all extracted tables

    returns:
        list of tables with structured data
    """
    try:
        tables_path = Path("data/processed/tables.json")
        if not tables_path.exists():
            return TableResponse(tables=[])

        with open(tables_path, "r") as f:
            tables_data = json.load(f)

        return TableResponse(tables=tables_data)
    except Exception as e:
        print(f"Error loading tables: {e}")
        return TableResponse(tables=[])
