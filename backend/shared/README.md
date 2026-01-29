# shared schemas

pydantic schemas for data interchange.

## usage

**data eng** (write):

```python
from shared.schemas import ProcessedDocument, Chunk

doc = ProcessedDocument(document_id=id, filename="x.pdf", chunks=chunks)
with open("data/processed/chunks.json", "w") as f:
    f.write(doc.model_dump_json(indent=2))
```

**ml/ai** (read):

```python
from shared.schemas import ProcessedDocument

with open("data/processed/chunks.json") as f:
    doc = ProcessedDocument.model_validate_json(f.read())
```

**full-stack** (api):

```python
from shared.schemas import TablesDocument

tables_doc = TablesDocument.model_validate_json(...)
return tables_doc.model_dump()
```

## schemas

- `ProcessedDocument` - chunks.json
- `TablesDocument` - tables.json
- `Chunk` - text/table chunk
- `Table` - structured table
