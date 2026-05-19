# Metodologia estatística

## Objetivo

Este projeto não tenta prever futebol como uma casa de apostas. A proposta é construir um modelo transparente de apoio à decisão para duas perguntas:

1. Quais jogadores brasileiros têm melhor evidência estatística para compor um XI titular por função tática?
2. Como o Brasil se compara com as principais seleções candidatas ao título da Copa?

A metodologia combina seleção multicritério, normalização de métricas por 90 minutos, ponderação por contexto competitivo e simulação Monte Carlo.

## 1. Seleção de jogadores por função tática

A escolha do XI parte de uma restrição real: uma equipe não é formada pelos onze maiores scores gerais. Ela precisa respeitar funções. Por isso, o modelo separa jogadores em papéis táticos:

- GK: goleiro
- RB: lateral direito
- CB: zagueiro
- LB: lateral esquerdo
- DM/CM: volante ou meio-campista central
- RW: ponta direita
- AM/SS: meia ofensivo ou segundo atacante
- LW: ponta esquerda
- ST: centroavante

Cada jogador concorre dentro da própria função. Isso evita comparar diretamente, por exemplo, um atacante com muitos gols contra um lateral que contribui mais em duelos, progressão e ações defensivas.

## 2. Normalização por 90 minutos

Jogadores têm minutagens diferentes. Comparar totais absolutos pode favorecer quem apenas jogou mais. Por isso, o modelo calcula métricas por 90 minutos quando possível:

- gols por 90
- assistências por 90
- participações em gol por 90
- passes-chave por 90
- desarmes por 90
- interceptações por 90

Essa técnica é comum em análise de futebol porque aproxima a produção para uma mesma unidade de tempo.

## 3. Score do jogador

O score atual é uma média ponderada interpretável:

```text
Player Score =
0.30 * performance por função
+ 0.20 * minutagem
+ 0.15 * força da liga
+ 0.15 * forma recente
+ 0.10 * uso na Seleção
+ 0.10 * encaixe tático
```

### Justificativa dos pesos

| Componente | Peso | Justificativa |
|---|---:|---|
| Performance por função | 0.30 | Principal evidência de entrega técnica na posição. |
| Minutagem | 0.20 | Reduz risco de escolher jogador sem ritmo ou com amostra muito baixa. |
| Força da liga | 0.15 | Contextualiza a dificuldade competitiva da produção. |
| Forma recente | 0.15 | Captura desempenho atual, sem depender só de reputação histórica. |
| Uso na Seleção | 0.10 | Considera adaptação ao ambiente da equipe nacional. |
| Encaixe tático | 0.10 | Valoriza compatibilidade com a função no sistema escolhido. |

Esses pesos são uma primeira hipótese de modelagem. Em uma versão madura, eles devem ser calibrados com validação histórica, análise de sensibilidade e comparação com decisões reais de convocação.

## 4. Modelo de força das seleções

A previsão da Copa usa um modelo composto, em vez de um único índice ajustável manualmente.

```text
Team Strength v2 =
0.25 * força base
+ 0.17 * ataque
+ 0.13 * meio-campo
+ 0.13 * defesa
+ 0.08 * goleiro
+ 0.10 * forma recente
+ 0.07 * histórico em torneios
+ 0.07 * profundidade de elenco
```

### Justificativa

O desempenho de uma seleção depende de múltiplas dimensões. Um país pode ter grande ataque, mas defesa frágil; outro pode ter elenco equilibrado, mas pouca profundidade. Separar componentes torna o modelo mais auditável e permite entender por que uma seleção aparece acima de outra.

## 5. Simulação Monte Carlo

Após calcular a força das seleções, o modelo usa simulação Monte Carlo para estimar chances de avanço em torneio.

A lógica é:

1. atribuir uma força estimada para cada seleção;
2. converter diferença de força em probabilidade de vitória com função logística;
3. simular milhares de campanhas;
4. contar quantas vezes cada seleção chega à semifinal, final e título;
5. transformar os resultados em probabilidades comparativas.

Esse tipo de abordagem é usado em previsões esportivas porque lida bem com incerteza. Futebol tem baixa pontuação e alta variância; por isso, uma única previsão determinística seria frágil.

## 6. Base científica e referências metodológicas

A metodologia se apoia em princípios comuns de modelagem esportiva:

- modelos tipo Elo usam diferença de força entre equipes para estimar resultado esperado;
- modelos de previsão de torneios costumam usar ratings, regressões ou força de equipe como entrada;
- simulações Monte Carlo são úteis para transformar probabilidades por jogo em probabilidades de campanha;
- modelos com variáveis de mercado e desempenho atual podem produzir estimativas úteis mesmo com poucos ingredientes, desde que as limitações estejam explícitas.

## 7. Papel do SportsDataverse/worldfootballR

A camada atual usa um CSV reprodutível para o MVP. Para uma versão com mais qualidade analítica, o projeto deve incorporar fontes como:

- API-Football para cobertura ampla de jogadores, clubes, competições e estatísticas básicas;
- SportsDataverse como ecossistema reprodutível de pacotes esportivos;
- worldfootballR para dados de futebol vindos de FBref, Transfermarkt e Understat;
- FBref para métricas avançadas por 90 minutos;
- Understat para xG e xA;
- Transfermarkt para valor de mercado, idade e profundidade de elenco;
- oddsapiR ou camada de odds para comparar o modelo com expectativa de mercado.

## 8. Limitações atuais

- A base de jogadores ainda é amostral.
- Os pesos ainda são definidos por hipótese analítica.
- O modelo ainda não usa grupos oficiais da Copa.
- Lesões, suspensões e fadiga ainda não entram automaticamente.
- Métricas avançadas como xG, xA, pressões, conduções progressivas e passes progressivos ainda não estão implementadas.

## 9. Próximas melhorias

1. Criar ingestão com API-Football e worldfootballR.
2. Armazenar dados em PostgreSQL.
3. Criar camada de métricas avançadas por função.
4. Validar pesos com histórico de jogos e convocações.
5. Substituir força manual por Elo/FIFA/odds/modelo treinado.
6. Simular grupos e chaveamento oficial da Copa.
