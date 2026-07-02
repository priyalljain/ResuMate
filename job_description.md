# Job Description: Senior AI Engineer — Founding Team

**Company:** Redrob AI (Series A AI-native talent intelligence platform)
**Location:** Pune/Noida, India (Hybrid) | Open to relocation candidates from Tier-1 Indian cities
**Employment Type:** Full-time
**Experience Required:** 5–9 years (soft range, not a hard cutoff)

## Let's be honest about this role

We're writing this JD differently from most. We're a Series A company that just raised our round and we're building a new AI Engineering org from scratch. This is the kind of role where the JD changes every six months because the company changes every six months. Instead of pretending we have a fixed checklist, we're going to tell you what we actually need and what we've gotten wrong before.

If you've spent your career at Google or Meta and you want a well-scoped role with a defined ladder, this isn't it. If you've spent your career bouncing between early-stage startups and you want to "just code" without having to think about product, recruiter workflows, or eval frameworks, this also isn't it.

We need someone who is simultaneously comfortable with two things that sound contradictory:

1. **Deep technical depth** in modern ML systems — embeddings, retrieval, ranking, LLMs, fine-tuning.
2. **Scrappy product-engineering attitude** — willing to ship a working ranker in a week even if the underlying ML is "obviously suboptimal," because we need to learn from real users before we know what to actually optimize for.

These are not contradictory in real life. They feel contradictory because of how engineering culture sorted itself into "researcher" vs "shipper" archetypes. We need both modes available in the same person, and we'd rather you tilt slightly toward shipper than toward researcher.

## What you'd actually be doing

The high-level mandate: own the intelligence layer of Redrob's product. That means the ranking, retrieval, and matching systems that decide what recruiters see when they search for candidates and what candidates see when they search for roles.

In practical terms, your first 90 days will probably look like:

* **Weeks 1-3:** Audit what we currently have (it's mostly BM25 + rule-based scoring, working but not great). Identify the 3-4 highest-leverage things to fix.
* **Weeks 4-8:** Ship a v2 ranking system that demonstrably improves recruiter-engagement metrics. This will involve embeddings, hybrid retrieval, and probably some LLM-based re-ranking, but the architecture is your call.
* **Weeks 9-12:** Set up the evaluation infrastructure — offline benchmarks, online A/B testing, recruiter-feedback loops — so we can keep improving without flying blind.

Beyond that, you'll be driving the long-term architecture of how we do candidate-JD matching at scale, mentoring the next round of hires (we're growing the team from 4 to 12 engineers in the next year), and working closely with our recruiter-experience PM on what to build.

## Disqualifiers (explicit)

* **Pure Research Backgrounds:** If you've spent your career in pure research environments (academic labs, research-only roles) without any production deployment — we will not move forward. We are explicit about this. We've tried it twice and it didn't work for either side.
* **Surface-Level AI Experience:** If your "AI experience" consists primarily of recent (under 12 months) projects using LangChain to call OpenAI — we will probably not move forward, unless you can demonstrate substantial pre-LLM-era ML production experience. We're looking for people who understood retrieval and ranking before it became fashionable.
* **Pure Architects/Leads:** If you are a senior engineer who hasn't written production code in the last 18 months because you've moved into "architecture" or "tech lead" roles — we will probably not move forward. This role writes code.

## Things you absolutely need

* Production experience with **embeddings-based retrieval systems** (`sentence-transformers`, OpenAI embeddings, BGE, E5, or similar) deployed to real users. We don't care which model — we care that you've handled embedding drift, index refresh, and retrieval-quality regression in production.
* Production experience with **vector databases or hybrid search infrastructure** — Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS, or something similar. Again, the specific tech doesn't matter; the operational experience does.
* **Strong Python skills.** Yes really, we care deeply about production code quality.
* Hands-on experience designing **evaluation frameworks for ranking systems** — NDCG, MRR, MAP, offline-to-online correlation, and A/B test interpretation. If you've never thought about how to evaluate a ranking system rigorously, this role will be very painful.

## Things we'd like but won't reject you for

LLM fine-tuning experience (LoRA, QLoRA, PEFT); experience with learning-to-rank models (XGBoost-based or neural); prior exposure to HR-tech, recruiting tech, or marketplace products; background in distributed systems or large-scale inference optimization; open-source contributions in the AI/ML space.

## Things we explicitly do NOT want

* **Title-chasers:** If your career trajectory shows you optimizing for "Senior" → "Staff" → "Principal" titles by switching companies every 1.5 years, we're not a fit. We need someone who plans to be here for 3+ years.
* **Framework enthusiasts:** If your GitHub is full of LangChain tutorials and your blog posts are "How I used [hot framework] to build [demo]" — that's fine but it's not what we need. We need people who think about systems, not frameworks.
* **IT Services Veterans:** People who have only worked at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc.) in their entire career. We've had bad fit experiences in both directions. If you're currently at one of these companies but have prior product-company experience, that's fine.
* **Out-of-Domain Specialists:** People whose primary expertise is computer vision, speech, or robotics without significant NLP/IR exposure. We respect your work but you'd be re-learning fundamentals here.
* **Closed-Box Engineers:** People whose work has been entirely on closed-source proprietary systems for 5+ years without external validation (papers, talks, open-source). We need to see how you think, not just trust that you can think.

## Location, comp, logistics

Pune/Noida preferred but flexible; we have physical offices in both locations (mostly used Tue/Thu). We don't require a specific number of in-office days but expect quarterly travel for offsites. Candidates currently based in Hyderabad, Pune, Mumbai, or Delhi NCR are welcome to apply. Outside India: evaluated case-by-case, but we do not sponsor work visas. Notice period: sub-30-day strongly preferred (we can buy out up to 30 days); 30+ day candidates are still in scope but the selection bar will be higher.

## The vibe check

We genuinely believe culture-fit matters more at this stage than skills-fit. Skills are teachable; the rest mostly isn't. We work async-first and write a lot—if you find writing painful, you'll find this role painful. We disagree openly and decide quickly. We move fast and break things, with the caveat that "things" are usually our internal assumptions, not user-facing production systems. If you need a stable, mature codebase to be productive, you'll find this role unstable.

## How to read between the lines (the ideal candidate)

Roughly: 6-8 years total experience, of which 4-5 are in applied ML/AI roles at product companies (not pure IT services). They have successfully taken at least one end-to-end ranking, search, or recommendation system to real users at meaningful scale. They possess strong, defensible opinions about retrieval (hybrid vs dense), evaluation (offline vs online), and LLM integration (when to fine-tune vs prompt)—and can back them up with reference to production systems they actually built.

We are looking for a needle in a haystack—an engineer who understands the core mechanics of search and retrieval before it became fashionable, and who values shipping over pure academic perfection.

## Note for hackathon participants

If you're reading this in the context of the Intelligent Candidate Discovery & Ranking Challenge:

The "right answer" to this JD is **not** to look for candidates whose skills section contains the most AI keywords. That's a trap we've explicitly built into the evaluation dataset. The right answer involves reasoning about the gap between what the JD says and what the JD means.

A Tier 1 candidate may not explicitly use the words "RAG" or "Pinecone" in their profile summary, but if their career history shows they built an end-to-end recommendation system at a product company, they're a fit. Conversely, a candidate who has all the AI buzzwords listed as skills but whose title is "Marketing Manager" or "Pure Researcher" is not a fit, no matter how perfect their keyword list looks.

Your ranking system should also weigh behavioral signals — a perfect-on-paper candidate who hasn't logged into the platform for 6 months and has a 5% recruiter response rate is, for hiring purposes, not actually available. Down-weight them appropriately. Good luck.