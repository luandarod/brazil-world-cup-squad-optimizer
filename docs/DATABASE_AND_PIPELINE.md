# Database and Processing Pipeline

## Visão geral

O projeto pode começar com CSV, mas a estrutura recomendada para uma versão profissional é usar um banco relacional. As melhores opções são:

- PostgreSQL, para desenvolvimento local e portfólio técnico.
- BigQuery, para demonstrar stack de analytics em nuvem.
- DuckDB, para uma versão leve, rápida e fácil de rodar localmente.

Para este projeto, a recomendação é:

```text
MVP local: CSV + DuckDB
Versão portfólio: PostgreSQL
Versão cloud: BigQuery
```

## Banco recomendado para subir primeiro

A primeira versão deve usar PostgreSQL, porque comunica bem conhecimentos de SQL, modelagem relacional e pipeline de dados.

Nome sugerido do banco:

```text
brazil_squad_optimizer
```

## Tabelas principais

### 1. players

Cadastro do jogador.

| Campo | Tipo | Descrição |
|---|---|---|
| player_id | integer | ID único do jogador na API ou ID interno |
| player_name | text | Nome do jogador |
| nationality | text | Nacionalidade |
| birth_date | date | Data de nascimento, quando disponível |
| age | integer | Idade |
| preferred_position | text | Posição principal |
| foot | text | Pé dominante, quando disponível |

### 2. teams

Cadastro de clubes.

| Campo | Tipo | Descrição |
|---|---|---|
| team_id | integer | ID do clube |
| team_name | text | Nome do clube |
| country | text | País do clube |
| league_id | integer | Liga principal |

### 3. leagues

Tabela de ligas e peso competitivo.

| Campo | Tipo | Descrição |
|---|---|---|
| league_id | integer | ID da liga |
| league_name | text | Nome da liga |
| country | text | País |
| league_weight | numeric | Peso competitivo usado no score |

### 4. player_season_stats

Tabela fato principal do projeto.

| Campo | Tipo | Descrição |
|---|---|---|
| player_id | integer | Jogador |
| season | integer | Temporada |
| team_id | integer | Clube |
| league_id | integer | Liga |
| position | text | Posição registrada |
| appearances | integer | Jogos |
| lineups | integer | Jogos como titular |
| minutes | integer | Minutos jogados |
| goals | integer | Gols |
| assists | integer | Assistências |
| shots_total | integer | Finalizações |
| shots_on | integer | Finalizações no alvo |
| passes_total | integer | Passes totais |
| passes_key | integer | Passes-chave |
| passes_accuracy | numeric | Acurácia de passes |
| yellow_cards | integer | Cartões amarelos |
| red_cards | integer | Cartões vermelhos |
| duels_total | integer | Duelos totais |
| duels_won | integer | Duelos vencidos |
| tackles_total | integer | Desarmes |
| interceptions | integer | Interceptações |
| rating | numeric | Nota média, quando disponível |

### 5. national_team_tests

Tabela para registrar escalações e testes da Seleção.

| Campo | Tipo | Descrição |
|---|---|---|
| match_date | date | Data do jogo/treino divulgado |
| coach | text | Treinador |
| opponent | text | Adversário |
| formation | text | Formação usada |
| player_id | integer | Jogador |
| position_used | text | Função usada na Seleção |
| started | boolean | Se foi titular |
| minutes_played | integer | Minutos jogados, quando disponível |

### 6. player_scores

Tabela derivada com o resultado do modelo.

| Campo | Tipo | Descrição |
|---|---|---|
| player_id | integer | Jogador |
| season | integer | Temporada |
| squad_role | text | Função no modelo: GK, RB, CB, LB, DM_CM, RW, AM_SS, LW, ST |
| performance_score | numeric | Score técnico por posição |
| minutes_score | numeric | Score de ritmo/minutagem |
| league_score | numeric | Score de nível competitivo |
| national_team_score | numeric | Score por uso na Seleção |
| tactical_fit_score | numeric | Score de encaixe tático |
| final_score | numeric | Score final de 0 a 100 |

## Fluxo de processamento

```text
API/CSV bruto
    ↓
data/raw
    ↓
limpeza e padronização
    ↓
data/processed
    ↓
feature engineering
    ↓
cálculo de scores
    ↓
otimização da escalação
    ↓
Streamlit / Power BI / relatório
```

## Camadas do pipeline

### 1. Ingestão

Responsável por buscar dados da API-Football ou ler CSVs manuais.

Arquivo principal:

```text
src/api_client.py
```

### 2. Limpeza

Converte colunas numéricas, remove registros sem minutos e padroniza nomes de jogadores, clubes e ligas.

Arquivo principal:

```text
src/data_cleaning.py
```

### 3. Feature engineering

Cria métricas comparáveis entre jogadores:

- gols por 90 minutos;
- assistências por 90;
- participações em gol por 90;
- passes-chave por 90;
- desarmes por 90;
- interceptações por 90;
- taxa de duelos vencidos;
- penalidade disciplinar;
- peso da liga.

Arquivo principal:

```text
src/feature_engineering.py
```

### 4. Score

Normaliza as métricas e calcula um score final de 0 a 100.

Arquivo principal:

```text
src/scoring_model.py
```

### 5. Otimização da escalação

Seleciona o melhor jogador por função dentro da formação 4-2-3-1.

Arquivo principal:

```text
src/squad_optimizer.py
```

## Como evoluir o banco

Primeiro passo:

```text
CSV → pandas → Streamlit
```

Segundo passo:

```text
API-Football → pandas → PostgreSQL → Streamlit
```

Terceiro passo:

```text
API-Football → BigQuery → dbt/SQL models → Looker/Power BI/Streamlit
```
