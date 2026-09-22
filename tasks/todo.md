# Modernize the Claude API integration (Opus 5.5, SDK 1.x, request shaping)

Triggered by the Opus 5.5 release: audit how PacketArch talks to Anthropic and
bring it current — model *and* API patterns.

## Plan

- [x] Audit every Anthropic touchpoint (router, provider, pricing, factory,
      both chat loops, Settings UI, key-test routes)
- [x] **Fix** Sonnet 5 mispricing ($3/$15 → $2/$10; the scheduled increase was
      cancelled, so the defensive rounding became a 50% over-report)
- [x] **Fix** the thinking allowlists failing closed on unknown model ids
- [x] **Fix** prompt-cache breakpoints sitting exactly at the 4-per-request cap
- [x] **Fix** refusals losing `stop_details` (category is the only diagnostic)
- [x] Route heavy tasks to `claude-opus-5-5`; add it to pricing + the dropdown
- [x] Declare `output_config.effort` per task
- [x] Replace the string-matched "Streaming is required" branch with a threshold
- [x] Classify SDK failures with the SDK's own exception types
- [x] Tool search + `defer_loading` for the 69-tool chat loop
- [x] Server-side context management on both chat loops
- [x] Make `/ai/chat/stream` actually stream
- [x] Upgrade `anthropic` 0.79 → 1.8, regenerate the lock
- [x] Tests for request shaping + response round-tripping
- [x] Verify: suite, build, live two-turn tool-search call, live streaming call

## Review

**Four live defects fixed.** The Sonnet 5 price was wrong in the cost
dashboard. The other three were latent traps that a routine "add the new model
to the dropdown" change would have sprung: no thinking on an unlisted model, a
400 on the fourth skill, and a refusal with no category.

**The capability table is the substantive change.** `THINKING_MODELS` /
`ADAPTIVE_THINKING_MODELS` became one `ModelCapabilities` table whose *default*
describes a current-generation model, so unknown ids get modern behaviour and
the table lists only the legacy exceptions. It shrinks as old models retire
instead of needing an edit per release. Written up in `lessons.md`.

**Tool search is the biggest runtime change.** The chat loop shipped all 69 MCP
tool schemas on every one of up to 15 iterations. Now 6 hot tools stay loaded
and the rest are `defer_loading`, discovered via BM25 search. This needed a
prerequisite fix: `_format_response` silently dropped every block type it
didn't recognise, and the loop replays exactly what it returns — so the
`server_tool_use` / `tool_search_tool_result` blocks would have vanished from
history and broken the next turn. Strict mode stays off; deferring does not
relax the 20-tool strict cap, because the grammar builds from the full toolset.

**Verified live, not just in tests.** A two-turn call confirmed Opus 5.5 with
`effort=high`, tool search finding a deferred tool, and the assistant content
replaying without a 400. A second call confirmed the streaming path: 50 text
deltas, a real summarized-reasoning block, and the terminal `final` event the
SSE route needs to execute tools.

**SDK bump was small.** Only one breaking call site (`temperature`, which no
caller passes) and no `httpx` work, because nothing hands an httpx object to
the SDK. The lock diff is anthropic + httpx2/httpcore2/truststore; no other pin
moved. 1272 tests pass on 1.8.0.

### Notes

- The persisted `anthropic_model` row still reads `claude-opus-5` on this
  install. That is correct and deliberate: the task router takes precedence for
  every call that declares a task, and the row is the fallback for callers that
  don't. Operators can switch it in Settings.
- Deferred but worth revisiting: server-side refusal fallbacks. Opus 5.5 widens
  the safety classifiers and PacketArch generates ICS attack playbooks, so a
  `cyber`-category decline is plausible. Now that `stop_details.category` is
  surfaced, the decision can rest on how often it actually fires.
