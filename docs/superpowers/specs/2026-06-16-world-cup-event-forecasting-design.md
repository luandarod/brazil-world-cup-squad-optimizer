# World Cup Event Forecasting Lab Design

## Summary

Evolve the current World Cup Forecasting Lab from a real-data truth viewer into a hybrid analytical platform that supports:

- observed match truth for completed 2026 World Cup matches;
- event-level forecasting for goals, shots, and cards when coverage exists;
- model comparison against already played matches;
- forward-looking projections for the remaining tournament;
- group-stage and knockout-stage tournament intelligence;
- player-context features based on confirmed and probable lineups, bench usage, and substitutions.

The public app should remain honest about what is observed, what is inferred, and what is unavailable. Empty artifacts should only exist when they genuinely cannot yet be published, not because the forecasting pipeline is missing.

## Current State

Today the repository already supports:

- a real observed truth layer for completed World Cup 2026 matches in `data/serving/observed_match_results.csv`;
- explicit coverage reporting in `data/serving/coverage_summary.csv`;
- team-level observed summaries in `data/serving/team_summary.csv`;
- a Streamlit app that surfaces observed truth, coverage, and methodology;
- a FIFA-first ingestion path with ESPN fallback for observed results.

Today the repository does not yet support:

- published match-level forecast rows;
- published model leaderboard rows;
- comparison of predicted versus observed performance by target or model;
- tournament projections for groups or knockout rounds;
- player-context features for lineups, bench usage, or substitutions.

## Product Direction

The approved direction is a `hybrid lab platform`.

The project should show both:

- technical depth in data engineering, feature construction, sports modeling, and evaluation;
- product maturity through a polished public app that communicates the state of the tournament and the forecasting system.

The app should become the public analytical surface of the platform, while the pipelines remain responsible for ingestion, feature generation, backtesting, and serving output creation.

## Goals

1. Publish non-empty prediction artifacts for the 2026 World Cup using real public data.
2. Compare multiple sports-relevant model families on already played matches using temporal evaluation.
3. Forecast the remaining tournament at match, group, and knockout levels.
4. Add player-aware context through confirmed lineups and observed substitutions for completed matches, and probable lineups for future matches.
5. Keep all public outputs explicit about truth coverage and modeling confidence.

## Non-Goals

This phase will not:

- invent card coverage if the source layer still does not support it;
- claim player-level certainty when only heuristic probable lineups are available;
- run heavyweight live training inside Streamlit;
- depend on a single fragile paid API as the only way to keep the product working.

## System Design

### 1. Truth Layer

The truth layer remains the foundation of the project. It should continue to prefer official or official-adjacent sources and only fall back when necessary.

Observed truth should include, when available:

- match identity and date;
- tournament stage and group;
- home and away teams;
- final goals;
- shots;
- cards when coverage exists;
- confirmed lineup context for completed matches;
- bench usage and substitution events;
- source metadata and retrieval timestamp.

The truth layer must clearly separate:

- completed observed matches;
- future scheduled matches;
- unavailable metrics.

### 2. Feature Layer

The feature layer should combine structural team strength, recent form, in-tournament performance, and player-context signals.

#### Team and match features

- Elo or equivalent international team strength rating;
- FIFA-like ranking or public team strength proxy;
- recent form over configurable windows;
- goals for and against trends;
- shots for and against trends;
- discipline trends when cards become available;
- stage, group, and tournament context;
- rest days and match sequence position;
- opponent-relative adjustments.

#### Player-context features

For completed matches:

- confirmed starters;
- available bench players;
- substitutions made;
- minutes proxies when available;
- offensive and defensive contribution proxies aggregated to team level.

For future matches:

- probable XI based on last starting lineups, recent usage, and recurrence;
- probable bench depth score;
- lineup stability score;
- substitution tendency score;
- availability confidence flag.

Player-level raw signals should be aggregated into publishable team-context features rather than forcing brittle player-by-player public claims everywhere in the app.

### 3. Model Layer

The project should be `event-first`.

Primary targets:

- `home_goals`
- `away_goals`
- `home_shots`
- `away_shots`
- `home_cards` when supported
- `away_cards` when supported

Derived outputs:

- likely winner;
- draw probability or draw classification proxy;
- likely scoreline;
- expected points and advancement implications.

#### Model families

The first public modeling stack should compare:

- sports baselines such as moving averages, team attack/defense strength, Elo-driven baselines, and Poisson-style scoring models;
- generalized regression approaches such as Elastic Net and count-appropriate regressions where supported;
- sports-appropriate ML baselines such as Random Forest and XGBoost;
- optionally one additional well-known model family if the data supports it without adding complexity for its own sake.

Each target should have its own leaderboard. The platform should not collapse all targets into one synthetic ranking that hides tradeoffs.

### 4. Evaluation Layer

Evaluation must be temporal and public-facing.

Rules:

- models may only train on matches that occurred before the scored match;
- no random train/test splits for public metrics;
- target-level metrics must be published separately;
- future forecasts must remain visually separate from backtested evaluation.

Metrics should include:

- `MAE` for goals, shots, and cards;
- `RMSE` where useful for dispersion context;
- outcome accuracy for derived winner signals;
- probability-oriented metrics such as Brier score or log loss if prediction probabilities are exposed.

### 5. Tournament Intelligence Layer

The platform should publish intelligence at three levels:

#### Match level

- forecast by model and target;
- observed versus predicted comparison once the match is played;
- lineup and substitution context;
- confidence or readiness messaging tied to data quality.

#### Group level

- observed standings;
- projected standings;
- advancement scenarios;
- group-level team strength and expected event profiles.

#### Knockout level

- likely bracket paths;
- likely advancing teams;
- probability of reaching each stage;
- stage-specific forecast summaries for likely future matchups.

## Data Sources

### Required public sources

- FIFA or official tournament structure when accessible;
- ESPN fallback for observed match results and basic event signals;
- public team rating sources such as Elo or equivalent public ranking data;
- public match schedule source for future fixtures.

### Preferred public enrichments

- public lineup sources for confirmed starting elevens and substitutions;
- public player usage or contribution sources if stable enough to keep the pipeline maintainable.

### Source policy

The platform must annotate or encode whether a signal is:

- observed;
- probable;
- unavailable.

No public artifact should imply certainty where only heuristic inference exists.

## Serving Contract

The existing serving contract should be expanded rather than replaced.

### Keep

- `observed_match_results.csv`
- `coverage_summary.csv`
- `team_summary.csv`

### Add

- `match_predictions.csv`
- `model_leaderboard.csv`
- `match_prediction_vs_actual.csv`
- `group_forecast_summary.csv`
- `knockout_forecast_summary.csv`
- `team_forecast_summary.csv`
- `methodology_status.csv`

### Proposed public semantics

`match_predictions.csv`

- one row per match, per model, per scoring snapshot as needed;
- predicted goals, shots, cards when supported, likely outcome, and confidence markers.

`model_leaderboard.csv`

- one row per model and target with temporal evaluation metrics and evaluation window metadata.

`match_prediction_vs_actual.csv`

- one row per played match and model showing predicted values, actual values, and errors.

`group_forecast_summary.csv`

- current group position, expected points, advancement probability, and group scenario indicators.

`knockout_forecast_summary.csv`

- probability of reaching round of 16, quarterfinal, semifinal, final, and title outcomes as supported by bracket state.

`team_forecast_summary.csv`

- observed and projected team-level indicators with player-context aggregate signals.

`methodology_status.csv`

- machine-readable readiness flags describing which targets are public, inferred, or unavailable.

## Public App Design

The Streamlit app should remain English-first in this phase and evolve into a fuller analytical product.

### Home

- tournament-status-first overview;
- observed match status;
- readiness of forecasting outputs;
- summary of what is observed, inferred, and unavailable.

### Model Leaderboard

- non-empty leaderboard by target and model;
- filters for target, evaluation window, and metric;
- explicit temporal evaluation messaging.

### Match Explorer

- played and future matches;
- predicted versus actual comparison where available;
- player-context readout for confirmed or probable lineups;
- substitutions and bench context for completed matches.

### Group and Knockout Views

- group tables and advancement scenarios;
- knockout progression probabilities and likely paths.

### Teams

- observed team summary plus projected event-level profile and depth indicators.

### Methodology

- source hierarchy;
- feature families;
- model families;
- target coverage rules;
- temporal evaluation principles;
- explanation of observed versus probable player context.

## Error Handling and Honesty Rules

- If cards do not have real coverage, cards remain unpublished or clearly marked unavailable.
- If probable lineups are heuristic only, the app must say so.
- If a fixture exists but the forecast cannot be scored yet, the app should explain that it is a future projection rather than a validated result.
- If a source fails, the platform should degrade to the strongest available fallback without silently changing semantics.

## Testing Strategy

Implementation should be backed by tests that cover:

- observed truth ingestion for matches, lineups, and substitutions;
- feature generation for team and player-context aggregates;
- temporal evaluation behavior that prevents leakage;
- serving output schemas and non-empty forecast artifacts when test fixtures support them;
- app contract tests for new labels, sections, and honest empty or unavailable states.

Key checks should include:

- predictions and leaderboard outputs are no longer empty by default in populated fixture scenarios;
- forecasts and observed comparisons are clearly distinguished;
- target coverage flags are preserved through the serving layer;
- player-context fields degrade safely when source data is missing.

## Delivery Strategy

The first implementation wave should prioritize:

1. truth and schedule enrichment with observed player-context data;
2. feature layer for team, match, and aggregated player signals;
3. sports baselines and temporal evaluation;
4. ML comparators for selected targets;
5. expanded serving outputs;
6. public app integration for leaderboard, match explorer, groups, and knockout views.

## Risks and Tradeoffs

- Public lineup sources may be less stable than score sources, so probable-lineup logic must degrade gracefully.
- Card coverage may lag other event families and should not block goals or shots publishing.
- Tournament simulation quality depends on both fixture completeness and team-strength priors; the app should describe that dependence.
- A broader model set increases maintenance cost, so the first public release should prefer a small set of strong comparators over a long list of shallow implementations.

## Acceptance Criteria

The design is complete for implementation when:

- the project can publish non-empty prediction and leaderboard artifacts for test and real snapshot scenarios;
- the app can compare already played matches against model outputs;
- the app can project remaining matches, groups, and knockout paths;
- player-context signals are visible as observed or probable rather than hidden;
- methodology and readiness messaging remain explicit and truthful.
