# World Cup 2026 Prediction Model

## Objetivo

Adicionar ao projeto uma camada de previsão de campanha do Brasil na Copa de 2026.

A pergunta passa a ser:

> Com base na força estimada do elenco, nível dos adversários e formato da Copa, até onde o Brasil tende a chegar?

## Formato considerado

A Copa de 2026 tem 48 seleções, 12 grupos de 4 equipes e uma fase eliminatória começando nos 32 avos de final. Classificam-se os dois primeiros de cada grupo e os oito melhores terceiros colocados.

## Abordagem estatística

O modelo inicial usa uma simulação de Monte Carlo simplificada.

### Índice de força

Cada seleção recebe um índice de força de 0 a 100.

Exemplo:

| Seleção | Strength Index |
|---|---:|
| França | 94 |
| Argentina | 93 |
| Brasil | 92 |
| Inglaterra | 91 |
| Espanha | 90 |

O índice pode ser refinado usando:

- Elo ratings;
- ranking FIFA;
- valor de mercado;
- score médio do elenco;
- gols esperados;
- desempenho nas eliminatórias;
- forma recente;
- lesões e suspensões.

## Probabilidade de vitória

A probabilidade de vitória é calculada com uma função logística.

```text
P(vitória) = 1 / (1 + exp(-(força_time - força_adversário) / escala))
```

Quanto maior a diferença de força, maior a probabilidade de vitória.

## Fase de grupos

Na fase de grupos, o modelo considera três resultados:

- vitória;
- empate;
- derrota.

O empate é mais provável quando as seleções têm força parecida.

## Mata-mata

No mata-mata, cada fase é simulada como um confronto eliminatório.

A dificuldade média dos adversários aumenta a cada fase:

| Fase | Força média do adversário |
|---|---:|
| Round of 32 | 74 |
| Round of 16 | 80 |
| Quartas | 85 |
| Semifinal | 89 |
| Final | 91 |

## Saídas do modelo

O modelo gera probabilidades para o Brasil alcançar:

- fase de grupos;
- 32 avos de final;
- oitavas;
- quartas;
- semifinal;
- final;
- título.

## Limitações

Esta primeira versão é um simulador explicável, não um modelo preditivo completo.

Limitações atuais:

- não usa tabela real de grupos se o usuário não fornecer;
- não usa lesões em tempo real;
- não simula chaveamento oficial completo;
- não usa odds de mercado;
- não usa Elo real atualizado automaticamente.

## Evolução ideal

Versão 2:

```text
Ranking FIFA/Elo + dados de elenco + grupos oficiais + simulação Monte Carlo completa
```

Versão 3:

```text
Modelo probabilístico por jogo com xG, forma recente, travel distance, descanso, lesões e força do adversário
```
