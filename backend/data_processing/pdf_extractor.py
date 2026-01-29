import os
import time
import requests
import asyncio
import httpx
import json
from typing import Optional, Dict, Any

DATALAB_API_URL = "https://www.datalab.to/api/v1/marker"

def _get_base_payload(force_ocr: bool, paginate: bool, max_pages: Optional[int]) -> Dict[str, str]:
    """Constructs the common payload for DataLab API."""
    payload = {
        "force_ocr": str(force_ocr).lower(),
        "paginate": str(paginate).lower(),
        "mode": "balanced",
        "output_format": "markdown",
        "skip_cache": "false",
        "save_checkpoint": "false",
        "format_lines": "false",
        "use_llm": "false",
        "strip_existing_ocr": "false",
        "disable_image_extraction": "false",
        "disable_ocr_math": "false",
    }
    if max_pages:
        payload["max_pages"] = str(max_pages)
    return payload

def _get_api_key() -> str:
    """Retrieves and validates the API key."""
    api_key = os.getenv('DATALAB_API_KEY')
    if not api_key:
        raise ValueError("DATALAB_API_KEY not found in environment variables.")
    return api_key

def extract_pdf_sync(
    file_path: str, 
    output_dir: str = "data/raw",
    max_pages: Optional[int] = None,
    force_ocr: bool = False,
    paginate: bool = True
) -> Dict[str, Any]:
    """
    Synchronously extracts text/markdown from a PDF using the DataLab API.
    Saves the full JSON response to the output_dir with the same basename.
    """
    api_key = _get_api_key()
    filename = os.path.basename(file_path)
    
    files = {
        "file": (filename, open(file_path, 'rb'), 'application/pdf')
    }
    
    payload = _get_base_payload(force_ocr, paginate, max_pages)
    headers = {"X-API-Key": api_key}
    
    print(f"Uploading {filename} to DataLab API...")
    # Note: 'files' dict with open file handle will be closed by requests if used as context or explicitly?
    # Requests does not automatically close files. It's better to use 'with open'.
    # Refactoring to use 'with open' context manager properly.
    
    with open(file_path, 'rb') as f:
        files = {"file": (filename, f, 'application/pdf')}
        response = requests.post(DATALAB_API_URL, data=payload, files=files, headers=headers)
    
    response.raise_for_status()
    
    init_data = response.json()
    check_url = init_data.get("request_check_url")
    if not check_url:
        return init_data

    # Poll for completion
    print(f"Job started. Polling for completion (URL: {check_url})...")
    max_polls = 300
    final_data = None
    
    for _ in range(max_polls):
        time.sleep(2)
        check_resp = requests.get(check_url, headers=headers)
        check_resp.raise_for_status()
        data = check_resp.json()
        
        if data["status"] == "complete":
            final_data = data
            break
        elif data["status"] == "error":
            raise RuntimeError(f"DataLab extraction failed: {data.get('error')}")
            
    if not final_data:
        raise TimeoutError("Timed out waiting for DataLab API to complete.")

    # Save to disk
    os.makedirs(output_dir, exist_ok=True)
    out_name = os.path.splitext(filename)[0] + ".json"
    out_path = os.path.join(output_dir, out_name)
    
    with open(out_path, "w") as f:
        json.dump(final_data, f, indent=2)
        
    print(f"Extraction complete. Saved to {out_path}")
    return final_data


async def extract_pdf_async(
    file_path: str, 
    output_dir: str = "data/raw",
    max_pages: Optional[int] = None,
    force_ocr: bool = False,
    paginate: bool = True
) -> Dict[str, Any]:
    """
    Asynchronously extracts text/markdown from a PDF using the DataLab API (via httpx).
    Saves the full JSON response to the output_dir with the same basename.
    """
    api_key = _get_api_key()
    filename = os.path.basename(file_path)
    
    payload = _get_base_payload(force_ocr, paginate, max_pages)
    headers = {"X-API-Key": api_key}
    
    async with httpx.AsyncClient() as client:
        print(f"[Async] Uploading {filename} to DataLab API...")
        
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = await client.post(DATALAB_API_URL, data=payload, files=files, headers=headers)
            response.raise_for_status()
            
        init_data = response.json()
        check_url = init_data.get("request_check_url")
        if not check_url:
            return init_data

        print(f"[Async] Job started. Polling for completion...")
        max_polls = 300
        final_data = None
        
        for _ in range(max_polls):
            await asyncio.sleep(2)
            check_resp = await client.get(check_url, headers=headers)
            check_resp.raise_for_status()
            data = check_resp.json()
            
            if data["status"] == "complete":
                final_data = data
                break
            elif data["status"] == "error":
                raise RuntimeError(f"DataLab extraction failed: {data.get('error')}")
        
        if not final_data:
            raise TimeoutError("Timed out waiting for DataLab API to complete.")

        # Save to disk
        os.makedirs(output_dir, exist_ok=True)
        out_name = os.path.splitext(filename)[0] + ".json"
        out_path = os.path.join(output_dir, out_name)
        
        with open(out_path, "w") as f:
            json.dump(final_data, f, indent=2)
            
        print(f"[Async] Extraction complete. Saved to {out_path}")
        return final_data
