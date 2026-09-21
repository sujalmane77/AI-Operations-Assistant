# Design Decisions

**Why LangGraph over a hand-rolled loop or a multi-agent framework?**
The required behavior — Think -> Retrieve -> Reason -> Act -> Observe -> Repeat —
maps directly onto LangGraph's StateGraph: each stage is a node, and the
loop-until-done condition is a conditional edge. A hand-rolled while-loop
would work too, but LangGraph gives structured state, easy checkpointing,
and clearer visual tracing for demos, at no cost since it's open-source.

**Why single-agent, not multi-agent?**
The task decomposes cleanly into one planning loop with pluggable tools,
not distinct roles/personas that need to negotiate or hand off work.
Multi-agent adds coordination complexity without adding capability here.

**Why local embeddings (sentence-transformers) instead of an embeddings API?**
Ingestion and repeated retrieval testing can mean many embedding calls.
Doing this locally means zero rate-limit risk and zero cost while
iterating, at the cost of slightly lower embedding quality than a top-tier
hosted model — an acceptable trade-off for an MVP over one document.

**Why Groq primary / Gemini fallback for reasoning?**
Both are free-tier and require no payment method. Groq's inference speed
matters specifically for this project because the agent loop can make
several LLM calls per user turn (planner decisions at each step); a slow
provider would make the multi-step loop feel sluggish. Gemini is the
fallback so a Groq outage/rate-limit doesn't take down the whole agent.

**Why "no hallucination" is enforced via system prompt + retrieval-first
instruction rather than a separate verifier step?**
For an MVP, a strong system prompt plus an explicit "say you don't know"
instruction is a reasonable first line of defense. A dedicated
fact-verification step (re-checking the final answer against retrieved
chunks) is a natural v2 addition, not required for the core demo.
