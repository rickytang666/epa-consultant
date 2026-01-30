# retrieval tuning results

**experiment date:** 2026-01-29
**script:** `backend/scripts/tune_retrieval.py`

## findings

we tested `top_k` values of 1, 3, and 5 against a factual qa suite.

| top-k | precision | token usage | verdict                                                             |
| ----- | --------- | ----------- | ------------------------------------------------------------------- |
| **1** | low       | low         | **insufficient**. missed context for multi-part answers.            |
| **3** | high      | optimal     | **selected**. consistent retrieval of all relevant sources.         |
| **5** | high      | high        | **inefficient**. added irrelevant chunks without improving quality. |

## decision

default `top_k` set to **3** to balance accuracy and latency/cost.
