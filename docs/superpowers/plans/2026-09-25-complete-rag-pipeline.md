# Household Business RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the household-business law corpus runnable through collection, indexing, hybrid retrieval, cited answers, Streamlit chat, and measured A/B evaluation.

**Architecture:** Keep the public functions and schemas in `docs/MODULE_CONTRACTS.md`. Use the existing Markdown corpus as the single source for chunking; persist dense vectors in Chroma and build BM25 over the same stable chunk IDs. Use a local extractive answer mode so the demo and evaluation work without credentials, with configurable cloud LLM providers for richer answers.

**Tech Stack:** Python, requests/BeautifulSoup, MarkItDown, scikit-learn, ChromaDB, rank-bm25, Streamlit, pytest.

**Spec:** `docs/MODULE_CONTRACTS.md`, `docs/STEP_BY_STEP.md`, `docs/GRADING_RUBRIC.md`, `docs/HKD_CORPUS.md`.

## Global Constraints

- Keep every public signature in `tests/test_contracts.py` unchanged.
- Do not send tests to external APIs.
- Keep source URLs and article IDs through retrieval and generation.
- Use original dense cosine scores for fallback decisions; RRF runs once.
- The offline evaluation must label its four lexical proxy metrics honestly and use the same questions and answer method for both configurations.
- Do not commit `.env`, Chroma data, model caches, or live API responses.

## Review Focus

- Existing snapshots must remain usable when remote pages are unavailable.
- Duplicate or malformed source articles must not enter the index.
- Chroma upsert must be idempotent and preserve stable IDs.
- Empty or out-of-domain queries must return a safe refusal.
- Citation labels in answers must resolve to returned source chunks.

---

### Task 1: Reproducible data stages

**Files:** `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `src/task3_convert_markdown.py`, `tests/test_data_pipeline.py`.

**Interfaces:** Existing `download_documents`, `crawl_article`, `crawl_all`, `convert_legal_docs`, `convert_news_articles`, and `convert_all` remain callable.

- [x] Write tests using local HTML/JSON/PDF fixtures for source extraction, reuse of cached snapshots, metadata, and idempotent conversion; run them and confirm they fail on the current stubs.
- [x] Implement Task 1 from the five saved Công báo page URLs, validating PDF headers; Task 2 from the six official article URLs, storing JSON; Task 3 as deterministic Markdown conversion that keeps the curated law files intact.
- [x] Run `python -m pytest tests/test_data_pipeline.py -q`, then the data acceptance tests.

### Task 2: Dense index and lexical search

**Files:** `src/task4_chunking_indexing.py`, `src/task5_semantic_search.py`, `src/task6_lexical_search.py`, `tests/test_contracts.py`, `tests/test_openrouter_embedding.py`, `.gitignore`, `.env.example`.

**Interfaces:** `load_documents`, `chunk_documents`, `embed_texts`, `embed_chunks`, `get_collection`, `index_to_vectorstore`, `semantic_search`, `lexical_search` preserve contract signatures.

- [x] Use contract tests for shared query embeddings, cosine conversion, and BM25 ordering; add a mocked OpenRouter API test.
- [x] Implement deterministic local dense embedding using char TF-IDF plus SVD, optional sentence-transformer mode, and OpenRouter embedding. Upsert batches to cosine Chroma; use the same chunks for BM25.
- [x] Run `python -m src.task4_chunking_indexing` and retrieval tests against both local and OpenRouter indexes.

### Task 3: Fusion, fallback, and cited generation

**Files:** `src/task7_reranking.py`, `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py`, `src/task10_generation.py`, `tests/test_contracts.py`, `tests/test_pageindex_fallback.py`.

**Interfaces:** Keep `rerank_rrf`, `pageindex_search`, `retrieve`, `reorder_for_llm`, `format_context`, and `generate_with_citation` signatures.

- [x] Run existing contract tests and add a PageIndex tree mapping test; demo safe refusal and provider failure behavior.
- [x] Implement one-pass RRF and dense-score fallback. PageIndex is optional and returns an empty list if unconfigured. Implement local extractive answers with numbered citations and configurable cloud generation providers.
- [x] Run contract and retrieval suites, then demo an in-domain and out-of-domain query.

### Task 4: UI and evaluation

**Files:** `app.py`, `src/evaluate.py`, `group_project/evaluation/RESULT.md`, `README.md`, `tests/test_evaluation.py`.

**Interfaces:** UI calls `generate_with_citation`; evaluation uses the existing 15-case `golden_dataset.json` and writes actual measured output.

- [x] Write tests for transparent metric computations and A/B configuration parity.
- [x] Render cited answers and clickable sources in Streamlit; run 15 cases for dense-only and hybrid with a shared extractive answer method, recording four explicitly defined offline proxy metrics and per-question errors.
- [x] Run `pytest -q`, inspect the generated report, and document the commands and credential-dependent limitations.

The PageIndex branch has no live key in this workspace. The earlier A/B report uses OpenRouter embeddings with extractive answers. The current `.env` uses Ollama `bge-m3:latest` embeddings: 399 chunks indexed. All 15 golden questions ran through the configured Gemini gateway with verified source quotations; results and proxy metrics are in `group_project/evaluation/RESULT_ONLINE.md`. Retrieval groups chunks by normalized source URL and filters mismatched numbered article/form anchors. The complete test suite passed (45 tests).
