# World Cup 2026 Simulation Design

Date: 2026-05-20
Repo: `brazil-world-cup-squad-optimizer`

## Goal

Evolve the current Brazil-only squad optimizer into a full **2026 FIFA World Cup simulation lab** that:

- uses **all qualified/provisionally called-up national teams**
- uses player data only from **2022 through 2026**
- projects probable starters and reserves
- simulates all matches, all phases, and podium outcomes
- generates match-level statistics such as goals by half, fouls, yellow cards, red cards, penalties, and expulsions
- compares multiple machine learning models, prioritizing **explainability first**
- supports **post-World Cup evaluation** against real 2026 outcomes

## Product Direction

The project is no longer just a “best Brazil squad” app. It becomes a **decision-oriented football simulation product** with four user-facing jobs:

1. Understand probable World Cup squads and lineups
2. Simulate single matches with detailed outcomes
3. Simulate the full tournament thousands of times
4. Compare model predictions against real tournament data after the World Cup

The main UI remains a **Streamlit application**.

## Core Assumptions

- Initial version uses **provisional 2026 squads**
- Final FIFA squads will be integrated later as an update
- Primary data source is **API-Football**
- **SportsMonks** acts as fallback for missing coverage
- **football-data.org** acts as validation for competition structure and schedule
- The app should not depend on live API calls during normal usage
- Data should be persisted locally in **DuckDB**

## Data Strategy

### Temporal scope

Only use player data between **2022-01-01** and the start of the 2026 World Cup.

Derived feature windows should include:

- full window: `2022-2026`
- recent form: last `12 months`
- short-term form: last `6 months`
- immediate form: last `3 months`

This avoids overweighting a player’s distant peak.

### Storage architecture

Use a local-first analytical stack:

- raw API snapshots in `data/raw`
- transformed tables in `data/processed`
- analytical serving layer in **DuckDB**

The Streamlit app reads from DuckDB rather than directly from APIs.

### Update strategy

- weekly refresh during development
- higher refresh frequency near the tournament
- optional post-match refresh during the tournament itself

### Update log

Maintain a local control table for:

- endpoint/source
- last refresh timestamp
- competition/season
- date range loaded
- row counts / optional freshness checks

This prevents re-pulling the full history on every run.

## Data Model

### Base tables

- `teams`
- `players`
- `competitions`
- `fixtures`
- `fixture_events`
- `fixture_lineups`
- `player_match_stats`
- `team_match_stats`
- `provisional_squads_2026`
- `final_squads_2026`
- `update_log`

### Derived tables

- `player_form_features`
- `team_strength_features`
- `projected_lineups`
- `simulation_runs`
- `simulation_match_outputs`
- `simulation_tournament_outputs`
- `post_world_cup_evaluation`

## Analytical Layers

### 1. Squad builder

This layer determines:

- squad membership
- probable starters
- probable reserves
- formation-specific lineup projections

It should support multiple tactical scenarios, at minimum:

- `4-2-3-1`
- `4-3-3`
- `3-4-3`

### 2. Team-strength layer

Each team receives an interpretable strength vector built from called-up players and projected lineups.

Recommended components:

- attack
- creation
- midfield control
- defense
- goalkeeper
- discipline
- squad depth
- continuity / chemistry proxy
- recent international form

This layer should remain transparent enough to explain why one team rates above another.

### 3. Match simulation layer

Do not use one monolithic black-box model for every output. Instead, split simulation into multiple explainable tasks:

- match result
- goals for each team
- goals by half
- fouls
- yellow cards
- red cards
- penalties
- expulsions

This keeps the system inspectable and easier to calibrate.

### 4. Tournament engine

The engine must simulate:

- group stage
- qualification / tie-breaking
- knockout rounds
- third-place match
- champion, runner-up, and third place

Run large Monte Carlo batches to estimate:

- qualification probability
- phase reach probability
- title probability
- podium probability

## Modeling Strategy

### First priority: explainable models

The first modeling wave should emphasize transparency and documentation.

Recommended initial family:

- multinomial / logistic classification for outcomes
- Poisson models for goals
- Negative Binomial variants for overdispersed count outcomes
- simple shallow trees or constrained boosting where useful
- rule-based baselines

### Second wave: stronger comparators

After the explainable baseline is stable, add stronger comparison models such as:

- random forest
- XGBoost or LightGBM
- simple ensembles

These are comparison layers, not the first modeling spine.

## Required Extensions

The project must include these four scenario layers:

### 1. Squad scenarios

Run simulations under:

- provisional squads
- final squads
- injury/removal variants
- alternative inclusion/exclusion scenarios

### 2. Tactical scenarios

Simulate the same team under different formations and probable XIs.

### 3. Uncertainty layer

Expose uncertainty caused by:

- limited minutes
- weak coverage
- stale form
- missing event-level detail
- low-confidence lineup assumptions

### 4. Model comparison layer

Compare multiple models and keep track of:

- tournament winner prediction quality
- match outcome quality
- event prediction quality
- calibration quality

## Streamlit Experience

The app should evolve into a simulation lab with at least these sections:

- `Data Status`
- `Squads and Projected XI`
- `Match Simulator`
- `Tournament Simulator`
- `Scenario Comparison`
- `Model Comparison`
- `Post-World Cup Evaluation`

The app should feel like an analytical product, not just a notebook wrapper.

## Post-World Cup Evaluation

After real 2026 data is available, update the project with actual outcomes and compare predictions vs. reality.

Evaluation targets should include:

- champion
- top 3
- progression by phase
- match results
- goals
- cards
- penalties
- event calibration

This closes the scientific loop and turns the repo into a true forecasting case study.

## Risks and Constraints

### Coverage risk

Provisional and final squad coverage may not come cleanly from one API. The design must allow manual/FIFA-assisted imports when needed.

### Rate-limit risk

The project should minimize repeated API pulls through local persistence and incremental updates.

### Calibration risk

Detailed match events are harder to simulate credibly than match outcomes. Event models should be introduced with explicit caveats and measured later against reality.

### Scope risk

This is a large project. Implementation should proceed in staged milestones rather than one single build.

## Recommended Build Order

1. Local data architecture with DuckDB and source ingestion
2. All-team squad + fixture pipeline for 2026
3. Projected lineups and team-strength layer
4. Explainable match simulation models
5. Tournament engine
6. Scenario system
7. Model comparison layer
8. Post-World Cup evaluation framework

## Success Criteria

The first strong version of the project succeeds if it can:

- ingest and persist all required 2022-2026 player/team/match data locally
- build provisional 2026 squads for all World Cup teams
- generate probable starters and reserves
- simulate the entire 2026 World Cup
- output podium probabilities
- compare multiple explainable models
- expose assumptions and uncertainty clearly in the Streamlit app

