# World Cup Forecasting Lab: Real-Data-Only Polish

## Objective

Polish the current World Cup Forecasting Lab so the public product only presents outputs grounded in real, traceable football data. The app must stop implying completeness when a metric or artifact is unavailable, and it must clearly distinguish observed match truth, model forecasts, and incomplete coverage.

## Problem Statement

The current repo already has a forecasting shell, evaluation contracts, and a public Streamlit app. However, the ingestion layer still contains stubs, and the app can read generic serving CSVs without making data provenance obvious. That creates a credibility gap for a portfolio project that is supposed to demonstrate production-minded analytics engineering.

The user also wants the project to remain anchored in real market signals and current concepts, not invented examples. That means this polish pass should prefer:

- official competition sources when available
- free public APIs when they add real coverage
- explicit nulls and coverage banners when data is not truly available

## Scope

This design covers:

- truth ingestion for already played matches
- transparent data coverage metadata for goals, cards, shots, lineups, and forecasts
- serving outputs that carry provenance and coverage fields
- app changes that surface real-data status instead of silently accepting empty or synthetic-looking files
- documentation updates about source hierarchy and limitations

This design does not cover:

- live scraping pipelines running continuously in production
- paid enterprise feeds as a hard dependency
- fabricated historical backfills for the 2026 tournament

## Approaches Considered

### 1. Strict official-only ingestion

Use only FIFA-controlled pages or APIs for observed match truth. If official sources do not expose cards, shots, or lineups in a stable way, those metrics stay unavailable.

Pros:

- strongest credibility
- simplest provenance story
- easiest to defend in interviews

Cons:

- may leave large gaps for advanced metrics
- official endpoints can be rate-limited or blocked to server-side requests

### 2. Hybrid public-source ingestion

Use FIFA as the primary truth source for match identity and scores, then optionally enrich missing fields from free public APIs or open datasets when coverage is transparent and source-specific.

Pros:

- better practical coverage
- still preserves data realism
- more representative of real analytics engineering work

Cons:

- requires source prioritization and reconciliation
- provenance logic becomes more important

### 3. UI-only transparency pass

Leave ingestion mostly as-is and just make the app more honest about missing data.

Pros:

- fastest implementation
- low engineering risk

Cons:

- does not close the main architecture credibility gap
- leaves stubs in the critical path

## Recommendation

Use approach 2.

The project should be explicit that official FIFA sources are the primary truth layer for completed matches, while free complementary sources can enrich non-score metrics when available. This is the best balance between honesty, technical depth, and portfolio value.

## Source Strategy

### Primary truth source

- FIFA tournament pages and supporting FIFA APIs for 2026 competition structure, fixtures, and completed scores.

### Optional complementary free sources

- `football-data.org` for fixtures, standings, squad context, and lineups within free-plan limits.
- `TheSportsDB` only as a fallback enrichment source when the needed field is not available elsewhere and provenance remains explicit.
- `API-Football` free tier as an optional development-time adapter, not as a required production dependency, because the free tier is limited by daily request volume.
- StatsBomb Open Data only for methodology examples or reusable event-modeling patterns, not as 2026 tournament truth unless the exact competition coverage exists.

### Source priority rules

1. Prefer official FIFA data for tournament identity, stage, date, teams, and final score.
2. Use complementary APIs only for fields FIFA does not expose accessibly.
3. Never overwrite official score truth with secondary sources.
4. Persist source attribution per field group or per row so downstream views can explain where each metric came from.

## Functional Design

### Truth ingestion

Replace the `FIFAClient` stub with a real client that:

- fetches accessible FIFA competition pages or APIs
- normalizes completed matches only
- returns structured raw payloads with source metadata

The truth dataset builder should:

- persist only observed matches
- include coverage columns such as `has_goals_truth`, `has_cards_truth`, `has_shots_truth`
- include source columns such as `score_source`, `discipline_source`, `shooting_source`

### Complementary enrichment

Add a small source adapter layer for optional enrichment. Adapters should be independent so the project can run even if a secondary source is not configured.

Expected behavior:

- if no complementary API key or free endpoint is available, the pipeline still succeeds
- enrichment fields remain null when unavailable
- the pipeline emits a coverage summary artifact for the app

### Serving layer

Serving outputs should include:

- observed matches summary
- coverage summary by metric
- model leaderboard filtered to metrics with actual truth coverage
- match predictions annotated with whether the match has already been observed

If there is not enough truth to compute a fair leaderboard for a metric, the serving output should omit or flag that comparison instead of manufacturing a ranking.

### Public app

The home page should become more executive and more explicit:

- count of observed matches loaded from real sources
- coverage badges for goals, cards, shots, and lineups
- next-step callouts showing what becomes available as more real matches are played

The model leaderboard tab should:

- show only evaluations supported by real truth
- explain when a model cannot yet be judged because truth coverage is incomplete

The match explorer should:

- distinguish upcoming fixtures from already played matches
- show actual result columns when a match is observed
- show prediction-vs-truth comparison when possible

The methodology tab should:

- explain source hierarchy
- document which metrics are official vs complementary
- state that missing metrics remain missing by design

## Data Model Changes

### Truth dataset additions

- `is_observed_match`
- `has_goals_truth`
- `has_cards_truth`
- `has_shots_truth`
- `score_source`
- `discipline_source`
- `shooting_source`
- `source_retrieved_at`

### Serving artifact additions

- `coverage_summary.csv`
- optional `observed_match_results.csv`

## Error Handling

- If FIFA data is unreachable, fail the ingestion command with a clear source-specific error.
- If complementary enrichment fails, log the failure and continue without that enrichment.
- If a serving artifact is missing, the app should render an explicit real-data status notice instead of a generic empty table message.

## Testing Strategy

Add tests for:

- real-data truth dataset schema and coverage flags
- serving behavior when only goals truth exists
- app rendering contract for coverage notices
- parser handling for partially available source fields

Preserve deterministic tests using recorded payload fixtures or narrow parser fixtures instead of depending on live network calls in CI.

## Implementation Plan Shape

The implementation should be done in three slices:

1. Replace truth stub flow with real-source parsing and coverage-aware dataset output.
2. Add serving artifacts and filtering rules based on real truth coverage.
3. Update the public app and documentation so every visible metric has an honest provenance story.

## Success Criteria

- No public-facing page implies model validation when real truth is missing.
- Completed matches are sourced from real competition data.
- Missing cards, shots, or lineup data remain visibly unavailable rather than synthesized.
- The repo communicates a production-style source hierarchy and resilience story.
- The app becomes stronger as additional real 2026 matches are played, without needing narrative rewrites.
