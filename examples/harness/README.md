# Pre-state routing examples

These are small illustrative tool-wrapper patterns, not production middleware or a
complete autonomous agent. Both demos use local mocked workers: no API key or paid
call. `routing.py` runs with the standard library. The graph uses the official
[StateGraph API](https://reference.langchain.com/python/langgraph/graph/state/StateGraph):
TypedDict state, a node returning a partial state update, START/END, compile/invoke.

```bash
python3 examples/harness/routing.py
python3 -m venv /tmp/open-shunt-example-env
/tmp/open-shunt-example-env/bin/pip install -r examples/harness/requirements.txt
/tmp/open-shunt-example-env/bin/python examples/harness/langgraph_example.py
/tmp/open-shunt-example-env/bin/python evals/harness_test.py
```

`run_harness(question, fetch)` or `build_graph(fetch)` without an injected delegate
uses the real worker: configure the existing SHUNT_PROVIDER, SHUNT_READER_MODEL and
API credentials or SHUNT_ADAPTER first. This invokes the existing Open Shunt
transport's `bulk-reader` task, not an invented company API. Real calls may incur
charges. No lead model call is included: returned messages are the boundary at
which your own harness would invoke its lead model.

`fetch` runs inside the routing function/node. Large results (>2000 UTF-8 bytes)
remain local until the worker returns <=2000 UTF-8 bytes. Only that answer becomes
a message/state update. Never split this into a raw-result graph node followed by
a summary node: the raw update may already be checkpointed or streamed.

Small results pass through unchanged. `exact=True` deliberately bypasses delegation
for exact/targeted work. Prefer a fetch that retrieves only needed lines; exact mode
can otherwise admit an arbitrarily large result. Caller policy, not model-generated
text, must authorize that flag. Empty/oversized answers and worker failures raise
DelegationFailed; no raw fallback is returned. The byte bound does not guarantee
semantic summarization or removal of quoted source snippets. Worker output remains
untrusted evidence.

This boundary is about lead context, not confidentiality: worker providers receive
raw data. Do not log raw fetch results or instrument fetch/delegate with tracing
that captures raw inputs/outputs; framework callbacks, exception instrumentation,
custom traces and external tools need their own redaction/retention policies.
Production integrations also need input authorization, observability, concurrency,
cancellation, retry/billing policy, persistence and explicit tool-call identifiers.
These examples use plain evidence messages, not a ToolMessage protocol loop.
