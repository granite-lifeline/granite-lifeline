# V4 metadata and semantic retrieval comparison

This directory is a historical evaluation snapshot. It predates the current
five-anomaly production knowledge base and must not be imported by runtime
code.

- `retrieval_comparison.py` and `retrieval_comparison.md` preserve the original
  seven-anomaly comparison.
- `historical_symptom_knowledge_indexer.py` recreates the historical
  seven-document collection used by that comparison. It writes to the local
  ignored `historical_chroma_db/` directory and cannot replace the production
  collection.
- `retrieval_comparison_5type_rerun.py` and its Markdown result repeat the
  comparison for the later five-anomaly knowledge base.

The production document-level indexer is
`report_layer/rag/symptom_knowledge_indexer.py`. Current report-quality evidence
is stored in `report_layer/evaluation/v5-rag-final-ablation/`.
