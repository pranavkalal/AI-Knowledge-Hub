# graphrag_research_review

# Deep Research Review: Knowledge Graphs, GraphRAG, Neo4j, and Strategy Options for Team Direction

## Scope

This document synthesizes the uploaded **Essential GraphRAG** book with current public research and documentation to support three decisions:

1. a deep research review of **knowledge graphs** and **GraphRAG**,
2. a **database evaluation of Neo4j** as the primary system for combining graph data with vector embeddings,
3. a **strategy review** comparing **Microsoft GraphRAG** with custom implementations and adjacent alternatives.

Where the book and the current ecosystem differ, this review favors the more recent primary source and notes the difference explicitly.

---

## Executive summary

The strongest high level conclusion is this:

**GraphRAG is not one pattern, it is a family of patterns.** The right choice depends on the type of questions your system must answer.

A standard vector RAG stack is often enough for local, passage-level lookup. But it becomes weaker when you need one or more of the following:

- cross-document entity linking,
- filtering, counting, sorting, and aggregation,
- multi-hop reasoning across entities and relations,
- explainability and provenance,
- corpus-level summarization or “what are the main themes?” style questions.

That is exactly where **knowledge graphs** help. The uploaded book argues that knowledge graphs are especially useful because they unify structured and unstructured data, support precise queries, and enable richer retrieval than chunk-only vector search.[B1]

For your team, the most defensible position is likely:

- **Use Neo4j as the primary operational database** if you need one system that can hold graph structure, chunks, embeddings, and graph traversals together.
- **Do not adopt Microsoft GraphRAG as the default architecture unless your primary workload is corpus-level sensemaking or query-focused summarization over large narrative or report-style corpora.** Microsoft GraphRAG is powerful, but its indexing pipeline is heavier, prompt sensitive, and historically more expensive than simpler graph-aware approaches.[W1][W2][W3]
- **Prefer a custom Neo4j-centered GraphRAG stack for enterprise RAG** when your team needs precision, hybrid retrieval, text2cypher, entity-centric retrieval, and explainability. This is the most practical path for merging graph data with vector embeddings and justifying design choices to stakeholders.[B1][W4][W5]
- **Borrow ideas from Microsoft GraphRAG selectively**, especially community summaries and local versus global retrieval mode separation, rather than inheriting the full pipeline uncritically.[B1][W1]

In plain terms:

- If the problem is **enterprise QA over connected business data**, a **custom Neo4j GraphRAG** is usually the best strategic fit.
- If the problem is **global summarization over long, messy text corpora**, **Microsoft GraphRAG** becomes much more compelling.
- If the problem is **low-cost experimentation with graph-enhanced retrieval**, recent alternatives like **LightRAG**, **KG²RAG**, and **FRAG** are important comparison points, but today they should be treated as research-informed design inspirations unless your team is ready to absorb framework risk.[W6][W7][W8]

---

## 1. Knowledge graphs and GraphRAG, deep research review

## 1.1 Why vanilla RAG is not enough

The uploaded book starts from a familiar position: LLMs are strong generators but have hard limits around stale knowledge, hallucinations, and missing private data.[B1] RAG helps by retrieving external context at run time instead of relying only on model memory.[B1]

However, chunk-only retrieval has structural weaknesses:

- it retrieves semantically similar passages but often misses exact relationships,
- it struggles with aggregation queries,
- it struggles with entity disambiguation,
- it often loses document boundaries and source coherence,
- it is weak on dataset-wide or “global” questions.

The book makes this point repeatedly. Unstructured retrieval is useful, but it is not sufficient for questions requiring filtering, counting, aggregation, or precise relational context.[B1]

### Practical implication

If your product requirements include questions like these, vector-only RAG is usually not enough:

- “Which supplier contracts expiring in the next 90 days mention indemnity caps above $1M?”
- “Which incidents involve the same customer, product, and region as the latest escalation?”
- “Summarize the main tensions and themes across all board minutes this quarter.”

The first two require **structured graph reasoning**. The third is where **GraphRAG-style summarization hierarchies** become valuable.

---

## 1.2 What knowledge graphs add to RAG

The book’s most durable insight is that knowledge graphs let you combine **structured facts** and **unstructured context** in one retrieval system.[B1] That matters because enterprise questions are rarely purely semantic or purely symbolic.

A knowledge graph improves RAG in five important ways:

### A. Entity grounding

Entity mentions in text can be linked to canonical nodes. This reduces duplication and improves retrieval consistency.

### B. Multi-hop retrieval

Graphs make it natural to traverse from one entity to related entities, events, documents, claims, or chunks.

### C. Precise filtering and aggregation

Graphs can answer questions that require counts, joins, constraints, and path-aware filtering. The book highlights that text alone cannot reliably answer these efficiently.[B1]

### D. Explainability

A graph traversal or a set of linked nodes and relationships is easier to inspect than a purely latent vector match.

### E. Hybrid retrieval

Graphs do not replace vectors. They complement them. The best systems typically use combinations of:

- vector similarity,
- keyword or full-text retrieval,
- graph traversal,
- structured query generation,
- reranking or agentic routing.

This “blend” perspective is central to the book and remains correct.[B1]

---

## 1.3 The main GraphRAG patterns that matter

The uploaded book is useful because it does not reduce GraphRAG to one architecture. It describes several patterns that matter in practice.[B1]

### Pattern 1, vector plus hybrid search

This is the entry point. Embed chunks, store them, retrieve by vector similarity, then add keyword search for hybrid retrieval. The book argues that hybrid retrieval is often better than pure vector retrieval because exact term matches and semantic similarity cover different failure modes.[B1]

**When to use it**

- FAQ assistants
- policy lookup
- document search
- low-complexity enterprise copilots

**Weakness**

Still weak for structured reasoning and global summarization.

### Pattern 2, advanced vector retrieval

The book covers step-back prompting and parent-document retrieval.[B1]

- **Step-back prompting** rewrites a narrow question into a broader one to improve retrieval recall.
- **Parent-document retrieval** embeds smaller child chunks but returns a larger parent context.

These are not graph-native ideas, but they often materially improve retrieval quality in graph-adjacent systems.

### Pattern 3, text2cypher

This is one of the most strategically important patterns for enterprise GraphRAG. The book shows how natural language can be converted to Cypher using schema, few-shot examples, terminology mappings, and formatting constraints.[B1]

**Why it matters**

This is how a system moves from “semantic passage search” to “actual database question answering.”

**Best for**

- aggregation queries,
- structured retrieval over business graphs,
- explainable queries,
- domain-specific assistants with stable schemas.

**Main risk**

Prompt fragility and schema drift. The book correctly recommends few-shot examples and explicit schema prompts to reduce generation errors.[B1]

### Pattern 4, agentic GraphRAG

The book presents agentic RAG as a router over multiple retrievers, plus an answer critic.[B1]

This pattern is especially useful when one retriever is never enough. For example:

- vector retrieval for unstructured context,
- graph traversal for neighbor discovery,
- text2cypher for exact structured questions,
- fallback tools for simpler cases.

This is increasingly how production systems are built, not because it is fashionable, but because enterprise questions vary widely.

### Pattern 5, graph construction from unstructured text

The book shows how LLMs can extract structured outputs from text and import them into a graph, using contracts as an example.[B1]

This pattern matters because many organizations do not start with a knowledge graph. They start with PDFs, emails, tickets, transcripts, policies, contracts, and reports.

### Pattern 6, Microsoft-style GraphRAG

This is a distinct branch of GraphRAG. It extracts entities and relationships, detects communities, summarizes those communities, then uses **global** and **local** query modes.[B1]

This is not just “graph plus vector.” It is a **hierarchical summarization architecture**.

---

## 1.4 Microsoft GraphRAG, what it actually is

According to Microsoft’s current documentation, GraphRAG is a structured, hierarchical RAG approach that extracts a graph from raw text, builds a community hierarchy, generates community summaries, and then uses those artifacts at query time.[W1] The official documentation currently exposes four main query modes:

- **Global Search**, for holistic corpus-level questions,
- **Local Search**, for entity-specific questions,
- **DRIFT Search**, for entity-centric search with community context,
- **Basic Search**, for standard top-k vector style retrieval.[W1]

This aligns closely with the book’s explanation of global and local search.[B1]

### Core strengths of Microsoft GraphRAG

1. **Excellent fit for global questions**
The original paper, *From Local to Global*, was explicit that conventional RAG struggles with questions like “What are the main themes in the dataset?” and that GraphRAG improves comprehensiveness and diversity on this class of query.[W9]
2. **Strong for narrative and report-like corpora**
GraphRAG works especially well when important information is spread across many chunks and needs to be synthesized.
3. **Architecturally clear separation of local and global retrieval**
That separation is strategically useful, even if you do not use Microsoft’s exact framework.
4. **Maturing tooling**
Microsoft released GraphRAG 1.0 in December 2024, citing a streamlined API layer, a simplified data model, and faster CLI startup.[W2]

### Main weaknesses of Microsoft GraphRAG

1. **Heavier indexing pipeline**
It requires more up-front LLM work than simpler graph-aware retrieval methods.[W1][W3]
2. **Prompt sensitivity**
Microsoft’s own docs recommend prompt tuning for your data rather than out-of-the-box defaults.[W1]
3. **Operational complexity**
Community detection, summarization layers, and multiple query modes create power, but also more moving parts.
4. **Potential overkill for enterprise graph QA**
If your dominant question type is entity-centric, transactional, or aggregation-heavy, text2cypher plus graph traversal can be more direct and cheaper.

### Bottom line on Microsoft GraphRAG

It is best understood as a **specialized architecture for large-scale, summarization-heavy, local-to-global reasoning over text corpora**.

That is narrower than the way some teams use the word “GraphRAG” in general discussion.

---

## 1.5 The newest Microsoft direction, LazyGraphRAG

This matters strategically because it changes how to interpret Microsoft’s own direction.

Microsoft Research introduced **LazyGraphRAG** in late 2024 as a lower-cost variant that defers expensive LLM work until query time. Microsoft reports that its indexing cost is the same as vector RAG and roughly **0.1% of full GraphRAG indexing cost**, while also reporting strong answer quality and dramatically lower query costs than full GraphRAG global search in the tested setup.[W3]

Separately, Microsoft’s BenchmarkQED announcement compared LazyGraphRAG against GraphRAG local, global, and DRIFT, plus Vector RAG, LightRAG, RAPTOR, and TREX, and reported that LazyGraphRAG outperformed the comparison conditions in that benchmark configuration.[W10]

### Why this matters for your justification

If the team wants to argue for or against “Microsoft GraphRAG,” the honest version is:

- Microsoft’s original GraphRAG is influential and important.
- Microsoft itself is already evolving beyond the original full indexing pipeline toward **cost-quality trade-off variants**.
- Therefore, “follow Microsoft GraphRAG” should not mean blindly adopting the earliest full pipeline. It should mean adopting the **parts that fit the workload**.

That actually strengthens the case for a selective, custom strategy.

---

## 2. Database evaluation, Neo4j for merged graph plus vector embeddings

## 2.1 Why Neo4j is a strong primary candidate

The uploaded book is explicitly Neo4j-centered and argues that graph databases are especially well suited for RAG because they can combine structured and unstructured data in one framework.[B1] That recommendation is directionally sound, and recent Neo4j releases have made the vector side more mature than it was in early 2024.[W4][W5]

Neo4j’s core value for GraphRAG is not just that it supports vectors. Many databases do that. Its value is that it combines:

- graph-native storage and traversal,
- Cypher query language,
- vector indexes,
- full-text search,
- graph-plus-vector retrieval in one operational surface,
- strong ecosystem integrations for GraphRAG patterns.

The strategic advantage is **co-location of symbolic and semantic retrieval**.

---

## 2.2 Neo4j capability review

### Graph-native modeling

Neo4j remains one of the strongest options for modeling entity-relation data with flexible traversal logic. This is the foundation for entity-centric GraphRAG.

### Vector indexing and search

Neo4j’s official documentation shows that vector indexes support approximate nearest-neighbor retrieval for node and relationship properties.[W4]

Recent changes are important:

- Neo4j introduced a native `VECTOR` data type in late 2025.[W11]
- As of Neo4j **2026.01**, vector indexes can include additional properties for filtering purposes, and the preferred query path becomes the Cypher `SEARCH` clause.[W4]

This is a notable improvement, because older Neo4j vector workflows often required awkward post-filtering.

### Full-text and hybrid search

Neo4j supports full-text indexes, and the Neo4j GraphRAG Python documentation includes hybrid retrievers and hybrid-cypher retrievers that combine vector retrieval with full-text retrieval and then traverse the graph for richer context.[W12]

### Graph plus vector retrieval inside one query surface

This is the part that matters most. You can retrieve semantically, traverse structurally, and constrain symbolically inside one database workflow. That is ideal for GraphRAG.

### Ecosystem support

Neo4j maintains GraphRAG-oriented tooling and integrations, including its Python GraphRAG packages and ecosystem connectors with frameworks such as LlamaIndex.[W12][W13]

---

## 2.3 Where Neo4j is especially strong

Neo4j is a very strong fit when most of the following are true:

- your data has explicit entities and relationships,
- you need multi-hop reasoning,
- you need explainability,
- you want one system for chunks, embeddings, entities, and traversals,
- you expect structured questions alongside semantic questions,
- you can define a domain schema or ontology over time.

Typical examples:

- contract intelligence,
- support knowledge assistants,
- product and customer graphs,
- regulatory or policy intelligence,
- incident and root-cause copilots,
- enterprise metadata hubs.

---

## 2.4 Where Neo4j is weaker or needs caution

Neo4j is not automatically the best choice in every case.

### A. If you only need vector search

If your workload is purely chunk retrieval with no meaningful graph logic, a dedicated vector database can be operationally simpler.

### B. Knowledge graph creation is not free

The graph does not create itself. Extraction, entity resolution, schema design, and quality control are real costs. The uploaded book explicitly highlights entity resolution as a critical and domain-specific step.[B1]

### C. Query generation quality matters

If you depend heavily on text2cypher, you must invest in:

- schema clarity,
- terminology mappings,
- few-shot examples,
- monitoring and evaluation.

The book is very clear about this.[B1]

### D. Very large-scale pure embedding workloads may favor specialized systems

For massive high-throughput ANN search where graph logic is secondary, specialized vector stores may still be simpler to scale operationally.

### E. Skills requirement

Teams need at least moderate graph literacy, especially around modeling and Cypher.

---

## 2.5 Neo4j verdict

**Verdict: recommended as the primary database if the team’s target system is genuinely graph-aware, not just vector-aware.**

That recommendation is strongest when you need:

- graph plus vector in one system,
- explainable retrieval,
- structured and unstructured fusion,
- extensibility toward agentic retrieval and text2cypher.

It is less strong if the use case is little more than semantic chunk retrieval.

---

## 3. Strategy review, Microsoft GraphRAG versus custom implementations

## 3.1 First, frame the decision correctly

This should not be framed as:

- “Microsoft GraphRAG versus Neo4j”

because they solve different layers of the stack.

A better framing is:

- **Microsoft GraphRAG** is a **retrieval and summarization architecture**.
- **Neo4j** is a **database and retrieval substrate** for graph-aware systems.
- A **custom implementation** can use Neo4j and still borrow Microsoft GraphRAG ideas.

So the real decision is:

- Do we want a **predefined hierarchical summarization architecture**, or
- do we want a **modular, custom GraphRAG stack** optimized for our domain?

---

## 3.2 Comparison table

| Criterion | Microsoft GraphRAG | Custom Neo4j GraphRAG |
| --- | --- | --- |
| Best fit | Corpus-level summarization, theme discovery, local-to-global reasoning | Enterprise QA, entity-centric retrieval, filtering, aggregation, explainability |
| Core mechanism | Entity extraction, community detection, community summaries, specialized query modes | Hybrid retrieval, graph traversal, text2cypher, agentic routing, optional summaries |
| Indexing cost | Higher, more LLM-heavy up front | Variable, can be much lighter |
| Prompt sensitivity | High, Microsoft recommends tuning | High for text2cypher, lower for deterministic traversals |
| Explainability | Good, especially with community/entity summaries | Very good, especially with explicit graph traversals and Cypher |
| Aggregation and exact structured queries | Indirect, not the main strength | Strong |
| Global “what are the themes?” questions | Strong | Can be built, but not automatic |
| Narrative corpus fit | Strong | Moderate unless you add summarization layers |
| Operational flexibility | Medium | High |
| Vendor or framework dependence | Higher | Lower |

### Interpretation

Choose **Microsoft GraphRAG** when the team’s hardest problem is **global summarization over large corpora**.

Choose **custom Neo4j GraphRAG** when the team’s hardest problem is **precise enterprise question answering over connected data**.

---

## 3.3 How to justify a custom approach against Microsoft GraphRAG

A custom approach is justified when at least three of these statements are true:

1. **Our dominant queries are local, structured, or entity-centric, not global sensemaking.**
2. **We need exact filtering, sorting, counting, and aggregation.**
3. **We need controllable provenance and explainability.**
4. **We already have or can build a useful domain graph.**
5. **We need to integrate multiple retrieval modes, not just one hierarchical summarization pipeline.**
6. **We want to control costs by avoiding heavy indexing unless the workload truly requires it.**

This is a strong argument because it is not anti-Microsoft. It is workload-driven.

---

## 3.4 How to justify Microsoft GraphRAG if the team leans that way

You should support Microsoft GraphRAG when the following are true:

1. The corpus is large, messy, and mostly unstructured.
2. The key user questions are broad, thematic, comparative, or corpus-wide.
3. Document-level chunk retrieval is clearly underperforming on comprehensiveness.
4. The team can absorb higher indexing and tuning complexity.
5. Community summaries have product value beyond QA, such as reporting or exploration.

This is exactly the class of problem the original GraphRAG paper targeted.[W9]

---

## 3.5 A middle-ground strategy that is often best

For many teams, the best answer is neither “pure Microsoft GraphRAG” nor “pure handcrafted graph QA.”

The strongest middle-ground strategy is:

### Recommended hybrid team direction

1. **Adopt Neo4j as the primary graph and vector substrate.**
2. **Start with custom hybrid retrieval**
    - vector search,
    - keyword search,
    - graph traversal,
    - text2cypher,
    - agentic routing if needed.
3. **Add selective Microsoft-inspired layers only where required**
    - entity summarization,
    - community summarization,
    - local versus global query mode separation.
4. **Use an evaluation framework from day one**
    - RAGAS-style metrics for answer correctness, faithfulness, and context recall, as used in the book,[B1]
    - and preferably a broader benchmark approach inspired by Microsoft’s BenchmarkQED for local/global question classes.[W14][W15]

This strategy is practical because it preserves optionality.

---

## 4. Other important alternatives to mention in the strategy review

A strong review should not compare only Microsoft GraphRAG and a generic “custom” path. There are newer research alternatives that sharpen the team’s understanding of the design space.

## 4.1 LightRAG

LightRAG proposes a dual-level retrieval system that integrates graph structures with vector representations and adds an incremental update mechanism. The ACL Anthology entry states that it improves retrieval accuracy and efficiency compared with existing approaches.[W6]

### Why it matters

LightRAG is important because it represents a design philosophy closer to “practical graph-enhanced retrieval” than to heavy community summarization.

### Strategic relevance

If the team wants something graph-aware but lighter than Microsoft GraphRAG, LightRAG is worth studying.

### Caveat

It is still best treated as research-led architecture, not a default enterprise standard.

---

## 4.2 KG²RAG

KG²RAG uses semantic retrieval to find seed chunks, then expands and organizes them using a knowledge graph to improve diversity and coherence of retrieved results.[W7]

### Why it matters

This is conceptually very attractive for systems that already have or can build a graph but do not want a full summarization hierarchy.

### Strategic relevance

KG²RAG strengthens the argument that **graph-guided chunk expansion** is a viable alternative to both naive top-k retrieval and full Microsoft GraphRAG.

---

## 4.3 FRAG

FRAG positions itself as a modular KG-RAG framework that tries to balance retrieval quality with flexibility. It estimates reasoning path complexity from the query and applies tailored pipelines without requiring extra model fine-tuning or additional LLM calls.[W8]

### Why it matters

FRAG is important because it directly addresses the trade-off between rigid modular systems and more coupled approaches.

### Strategic relevance

For your team, FRAG is a useful conceptual benchmark when discussing whether a custom GraphRAG stack should be **query-adaptive** rather than fixed.

---

## 4.4 LazyGraphRAG

Although it comes from Microsoft, it deserves its own entry because it is strategically different from the original GraphRAG.

Microsoft describes LazyGraphRAG as a lower-cost approach that blends best-first and breadth-first search, defers more LLM work to query time, and achieved very strong cost-quality trade-offs in Microsoft’s reported experiments.[W3]

### Strategic relevance

If the team likes Microsoft’s direction but worries about indexing cost and operational complexity, LazyGraphRAG is the most important recent signal that the architecture space is moving toward **cheaper, more flexible graph-aware retrieval**.

---

## 5. Evaluation guidance for the team

The uploaded book’s evaluation chapter is especially useful because it gives a pragmatic baseline. It uses three key metrics:

- **context recall**,
- **faithfulness**,
- **answer correctness**.[B1]

In the example benchmark, the reported summary scores were:

- answer correctness: **0.7774**
- context recall: **0.7941**
- faithfulness: **0.9657**[B1]

The important lesson is not the raw numbers. The lesson is that GraphRAG systems should be judged on at least three distinct axes:

1. **Did we retrieve the needed evidence?**
2. **Did the answer stay grounded in that evidence?**
3. **Was the answer actually correct and complete?**

Microsoft’s BenchmarkQED extends that logic toward broader local/global query generation and evaluation at scale.[W14][W15]

### Recommended evaluation plan

For your team, build a benchmark with four buckets:

- **local factual** questions,
- **structured/aggregation** questions,
- **multi-hop relational** questions,
- **global summarization** questions.

That benchmark design will make the strategy decision much easier, because it will reveal whether Microsoft GraphRAG’s global strengths are actually relevant to your workload.

---

## 6. Recommended team direction

## Recommended decision

**Adopt a custom Neo4j-centered GraphRAG as the primary direction, and incorporate Microsoft GraphRAG ideas selectively rather than wholesale.**

### Why this is the strongest recommendation

1. **It matches the broadest enterprise need surface.**
Most enterprise assistants need a mix of semantic retrieval, exact lookup, aggregation, and graph traversal.
2. **Neo4j is now mature enough on the vector side to justify a unified graph-plus-vector architecture.**
Current Neo4j documentation shows meaningful progress, including modern vector indexing, a native vector type, and in-index filtering support in current releases.[W4][W11]
3. **The custom route preserves workload fit.**
You can build exactly the retrievers your domain needs, instead of inheriting a summarization-heavy pipeline by default.
4. **Microsoft GraphRAG remains valuable, but as a pattern library, not necessarily as the whole product architecture.**
Its biggest ideas, especially local/global separation and summary hierarchies, are useful. Its full pipeline is only justified for certain workloads.[W1][W9]
5. **Recent research trends favor adaptive, lower-cost graph-aware retrieval.**
LightRAG, KG²RAG, FRAG, and LazyGraphRAG all point in that direction.[W3][W6][W7][W8]

---

## 7. Suggested implementation roadmap

### Phase 1, minimum viable GraphRAG

- Neo4j as the graph-plus-vector store
- chunk embeddings and full-text indexes
- hybrid retrieval
- graph schema for core entities and documents
- source-linked chunk provenance
- benchmark covering local, structured, multi-hop, and global queries

### Phase 2, enterprise retrieval maturity

- text2cypher for structured questions
- agentic routing between retrievers
- entity resolution workflow
- graph traversal-based context expansion
- reranking and metadata-aware filtering

### Phase 3, Microsoft-inspired additions only if needed

- entity summaries
- community detection
- local versus global query modes
- corpus-level thematic answer generation

### Phase 4, strategy validation

- compare against a Microsoft GraphRAG or LazyGraphRAG baseline on the same benchmark
- compare cost, latency, comprehensiveness, and faithfulness
- keep whichever architecture wins on your real query mix

---

## 8. Risks and mitigations

### Risk 1, graph extraction quality is noisy

**Mitigation:** start with human-curated core entities and relations for the highest-value domain objects, then layer LLM extraction on top.

### Risk 2, text2cypher is brittle

**Mitigation:** use schema prompts, terminology mappings, few-shot examples, and fallback tools, exactly as recommended in the book.[B1]

### Risk 3, overengineering with Microsoft GraphRAG

**Mitigation:** only add community summaries if benchmark evidence shows a real gap on global questions.

### Risk 4, cost growth

**Mitigation:** benchmark cheaper graph-aware retrieval baselines first, and treat full summarization indexing as an earned optimization, not a default assumption.

### Risk 5, poor evaluation discipline

**Mitigation:** formalize benchmark sets before architecture debates harden into opinion.

---

## 9. Final position you can defend to the team

You can defend the following position cleanly:

> We should treat GraphRAG as a toolbox, not a single framework. For our main direction, Neo4j is the strongest primary database when we need to merge graph data with vector embeddings and support both semantic and structured retrieval. Microsoft GraphRAG is a valuable architecture for global summarization over large unstructured corpora, but it should be adopted selectively, and only where our benchmark shows that community-summary style retrieval materially outperforms a simpler custom Neo4j GraphRAG stack.
> 

That position is technically grounded, current, and hard to dismiss as either anti-research or anti-practicality.

---

## References

### Core book

- **[B1]** Tomaž Bratanič and Oskar Hane, *Essential GraphRAG: Knowledge Graph-Enhanced RAG*, Manning, 2025. Source used here: uploaded project PDF, including chapters on hybrid retrieval, parent-document retrieval, text2cypher, agentic RAG, knowledge graph construction, Microsoft GraphRAG, and evaluation. Also see the companion repository: https://github.com/tomasonjo/kg-rag

### Microsoft GraphRAG and evaluation

- **[W1]** Microsoft GraphRAG documentation, “Welcome / Overview / Query modes.” https://microsoft.github.io/graphrag/
- **[W2]** Microsoft Research, “Moving to GraphRAG 1.0 – Streamlining ergonomics for developers and users,” Dec 16 2024. https://www.microsoft.com/en-us/research/blog/moving-to-graphrag-1-0-streamlining-ergonomics-for-developers-and-users/
- **[W3]** Microsoft Research, “LazyGraphRAG: Setting a new standard for quality and cost,” Nov 25 2024, updated Jun 6 2025. https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
- **[W9]** Edge et al., “From Local to Global: A Graph RAG Approach to Query-Focused Summarization,” Apr 2024. Microsoft Research page: https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/
- **[W10]** Microsoft Research, “BenchmarkQED: Automated benchmarking of RAG systems,” Jun 5 2025. https://www.microsoft.com/en-us/research/blog/benchmarkqed-automated-benchmarking-of-rag-systems/
- **[W14]** BenchmarkQED GitHub repository. https://github.com/microsoft/benchmark-qed
- **[W15]** BenchmarkQED documentation. https://microsoft.github.io/benchmark-qed/

### Neo4j

- **[W4]** Neo4j Cypher Manual, “Vector indexes.” https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
- **[W5]** Neo4j GenAI plugin docs, “Create and store embeddings.” https://neo4j.com/docs/genai/plugin/25/embeddings/
- **[W11]** Neo4j developer blog, “Introducing Neo4j’s Native Vector Data Type,” Nov 19 2025. https://neo4j.com/blog/developer/introducing-neo4j-native-vector-data-type/
- **[W12]** Neo4j GraphRAG Python docs, “User Guide: RAG.” https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html
- **[W13]** Neo4j Labs, LlamaIndex integration overview. https://neo4j.com/labs/genai-ecosystem/llamaindex/

### Other GraphRAG-related approaches

- **[W6]** Guo et al., “LightRAG: Simple and Fast Retrieval-Augmented Generation,” Findings of EMNLP 2025. ACL Anthology entry: https://aclanthology.org/2025.findings-emnlp.568/
- **[W7]** Zhu et al., “Knowledge Graph-Guided Retrieval Augmented Generation,” NAACL 2025. ACL Anthology entry: https://aclanthology.org/2025.naacl-long.449/
- **[W8]** Gao et al., “FRAG: A Flexible Modular Framework for Retrieval-Augmented Generation based on Knowledge Graphs,” Findings of ACL 2025. ACL Anthology entry: https://aclanthology.org/2025.findings-acl.321/