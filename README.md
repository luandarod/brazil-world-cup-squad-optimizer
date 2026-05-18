# Brazil World Cup Squad Optimizer

Projeto de dados para estimar o melhor time do Brasil para a Copa com base em estatísticas de jogadores, minutagem, nível competitivo da liga, posição, forma recente e uso em escalações/testes da Seleção.

## Objetivo

Responder à pergunta:

> Se a Seleção Brasileira fosse montada hoje, quais jogadores deveriam ser titulares e reservas com base em dados?

O projeto usa uma abordagem de score multicritério por posição, permitindo comparar jogadores brasileiros em diferentes ligas e funções.

## Principais entregas

- Coleta de dados via API de futebol.
- Base tratada com jogadores brasileiros.
- Normalização por 90 minutos.
- Pesos por liga.
- Score por posição.
- Simulação de escalação em 4-2-3-1.
- Comparação entre seleção por dados e jogadores testados na Seleção.
- App em Streamlit para visualização.
- Estrutura pronta para dashboard em Power BI/Looker.

## Fontes de dados sugeridas

Fonte principal recomendada:

- API-Football / API-Sports: dados de jogadores, clubes, ligas, temporadas, partidas e estatísticas.

Fontes complementares:

- football-data.org
- StatsBomb Open Data
- dados manuais de escalações/testes da Seleção a partir de fontes jornalísticas e escalações oficiais.

## Estrutura do projeto

```text
brazil-world-cup-squad-optimizer/
│
├── app/
│   └── streamlit_app.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── reference/
│
├── notebooks/
│   └── 01_exploratory_analysis.ipynb
│
├── src/
│   ├── api_client.py
│   ├── config.py
│   ├── data_cleaning.py
│   ├── feature_engineering.py
│   ├── scoring_model.py
│   └── squad_optimizer.py
│
├── reports/
│   └── executive_summary.md
│
├── requirements.txt
├── .env.example
└── README.md
```

## Como rodar localmente

1. Clone o repositório:

```bash
git clone https://github.com/SEU-USUARIO/brazil-world-cup-squad-optimizer.git
cd brazil-world-cup-squad-optimizer
```

2. Crie um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows:

```bash
.venv\Scripts\activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure a chave da API:

```bash
cp .env.example .env
```

Depois edite o arquivo `.env` com sua chave da API-Football.

5. Rode o app:

```bash
streamlit run app/streamlit_app.py
```

## Modelo de score

O score final usa uma estrutura ponderada:

```text
Score Final =
0.30 * performance por posição
+ 0.20 * minutagem
+ 0.15 * nível da liga
+ 0.15 * forma recente
+ 0.10 * uso na Seleção
+ 0.10 * encaixe tático
```

Os pesos mudam por posição. Um atacante é avaliado mais por gols, assistências e participação ofensiva; um zagueiro recebe mais peso por duelos, jogo aéreo, minutos e disciplina; um goleiro recebe mais peso por defesas, clean sheets, gols sofridos por 90 e saída de bola.

## Formação inicial

O MVP usa 4-2-3-1:

- 1 goleiro
- 1 lateral direito
- 2 zagueiros
- 1 lateral esquerdo
- 2 volantes/meias centrais
- 1 ponta direita
- 1 meia/segundo atacante
- 1 ponta esquerda
- 1 centroavante

## Exemplo de saída esperada

```text
Titular sugerido:
Alisson;
Wesley, Gabriel Magalhães, Bremer, Douglas Santos;
Casemiro, Bruno Guimarães;
Raphinha, Matheus Cunha, Vini Jr;
Igor Thiago.
```

## Observação

Este projeto não substitui análise técnica de comissão. A proposta é criar uma ferramenta de apoio baseada em dados, com critérios transparentes e ajustáveis.
