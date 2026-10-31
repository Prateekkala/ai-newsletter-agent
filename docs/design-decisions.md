# Design decisions

1. **Pipeline, not a free-roaming agent.** Each stage has a fixed input and output, so runs are cheap, predictable and easy to test. An agentic step (follow-up search, fact-check) can be added later where it earns its keep.
2. **RSS only for v1.** Free, stable and enough signal. Other sources can plug into `collect.py` later.
3. **Per-source failure isolation.** One dead feed is logged and skipped.
4. **Dedupe before any LLM call.** Cheaper and cleaner than asking a model to spot repeats.
5. **Human review before publishing.** Issues will land as a pull request to approve.
