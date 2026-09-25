# Evaluation Result

## Overall scores

The local corpus and retrieval contracts are available. Provider-backed generation metrics are not claimed here because no live OpenRouter API key was available during this run.

## A/B comparison

The comparison configuration is dense-only versus BM25 plus one-pass RRF hybrid retrieval. Contract tests cover dense, lexical, RRF, fallback, citation formatting, and safe refusal behavior.

## Worst performers

Queries requiring facts absent from the collected documents are expected to receive a safe refusal. Short keyword-only queries may also need threshold calibration on a larger golden set.

## Recommendations

Run the 15-case golden set with a configured provider, record faithfulness, answer relevance, context recall, and context precision, then tune the dense score threshold using both in-domain and out-of-domain queries.
