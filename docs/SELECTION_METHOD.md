# Selection Method

## Objetivo do método

O método não tenta dizer quem é o melhor jogador de forma absoluta. Ele tenta responder uma pergunta mais prática:

> Quem entrega mais valor para uma função específica dentro da formação escolhida?

Por isso, o modelo combina desempenho, ritmo competitivo, nível da liga, histórico recente na Seleção e encaixe tático.

## Formação base

A formação inicial usada é o 4-2-3-1.

```text
                 ST

LW              AM/SS              RW

          DM/CM        DM/CM

LB          CB          CB          RB

                 GK
```

## Funções avaliadas

| Função | Descrição |
|---|---|
| GK | Goleiro |
| RB | Lateral direito |
| CB | Zagueiro |
| LB | Lateral esquerdo |
| DM_CM | Volante/meio-campista central |
| RW | Ponta direita |
| AM_SS | Meia ofensivo ou segundo atacante |
| LW | Ponta esquerda |
| ST | Centroavante |

## Score final

O score final é uma média ponderada, em escala de 0 a 100.

```text
Final Score =
performance_score * 0.30
+ minutes_score * 0.20
+ league_score * 0.15
+ recent_form_score * 0.15
+ national_team_score * 0.10
+ tactical_fit_score * 0.10
```

## Componentes do score

### 1. Performance score

Avalia o que o jogador produziu na função dele.

Para atacantes:

- gols por 90;
- assistências por 90;
- participações em gol por 90;
- finalizações;
- passes-chave.

Para meio-campistas:

- passes-chave;
- passes certos;
- ações defensivas;
- duelos vencidos;
- participações em gol;
- minutos.

Para defensores:

- duelos vencidos;
- desarmes;
- interceptações;
- disciplina;
- minutos;
- contribuição ofensiva em bola parada.

Para goleiros:

- minutos;
- clean sheets, quando disponível;
- defesas, quando disponível;
- gols sofridos por 90, quando disponível;
- nota média.

### 2. Minutes score

Mede ritmo competitivo.

Exemplo:

| Minutos na temporada | Interpretação |
|---:|---|
| 2400+ | Ritmo muito alto |
| 1800-2399 | Ritmo bom |
| 900-1799 | Ritmo moderado |
| 300-899 | Risco de falta de ritmo |
| <300 | Baixa confiabilidade |

### 3. League score

Aplica peso pelo nível competitivo da liga.

Exemplo inicial:

| Liga | Peso |
|---|---:|
| Premier League | 1.00 |
| LaLiga | 0.95 |
| Serie A | 0.92 |
| Bundesliga | 0.90 |
| Ligue 1 | 0.86 |
| Brasileirão Série A | 0.82 |
| Saudi Pro League | 0.72 |
| Liga Russa | 0.70 |
| Süper Lig | 0.70 |

### 4. Recent form score

Pode ser calculado com os últimos jogos, caso a API disponibilize esse recorte.

No MVP, ele ainda é aproximado por:

- nota média;
- produção por 90;
- minutos jogados.

### 5. National team score

Mede se o jogador já foi usado/testado pela Seleção.

Critérios sugeridos:

| Situação | Bônus |
|---|---:|
| Titular recente da Seleção | +10 |
| Convocado recente | +6 |
| Testado na função do modelo | +5 |
| Nunca usado recentemente | 0 |

### 6. Tactical fit score

Mede se o jogador encaixa na função.

Exemplo:

- Vini Jr como LW: alto encaixe.
- Raphinha como RW: alto encaixe.
- Neymar como AM/SS: alto encaixe, mas pode ter penalidade de minutagem.
- Danilo como RB/CB: versátil, mas depende da função.

## Regras de seleção

O algoritmo segue estas etapas:

1. Calcula métricas por 90 minutos.
2. Normaliza indicadores para escala comparável.
3. Aplica peso por liga.
4. Penaliza baixa minutagem e excesso de cartões.
5. Aplica bônus por uso recente na Seleção.
6. Mapeia cada jogador para uma função no 4-2-3-1.
7. Seleciona o melhor score por função.
8. Gera o banco com os melhores jogadores restantes.

## Por que não basta pegar o maior score geral?

Porque uma escalação precisa respeitar posição e função.

Um atacante pode ter score maior que um lateral, mas isso não significa que ele deve ocupar uma vaga defensiva. Por isso, o modelo primeiro separa os jogadores por função e depois escolhe os melhores dentro de cada função.

## Limitações atuais

- O MVP usa base de exemplo.
- A camada de lesões ainda não foi implementada.
- O modelo não calcula química entre jogadores.
- O peso por liga ainda é manual.
- Dados de Seleção são manuais na primeira versão.

## Melhorias futuras

- Incluir xG e xA.
- Incluir dados de pressão, condução e progressão.
- Criar modelos diferentes por formação.
- Adicionar risco físico e histórico de lesões.
- Comparar seleção por dados vs seleção provável do treinador.
- Rodar simulações por adversário.
