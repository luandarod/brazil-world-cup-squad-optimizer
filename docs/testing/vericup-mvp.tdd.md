# Evidência TDD do VeriCup MVP

| Limite | RED | GREEN |
|---|---|---|
| TxLINE | módulo ausente | cliente validado e proxy server-side |
| Keeper | comportamento ausente | lifecycle/replay/worker cobertos |
| Mercado Anchor | instruções ausentes | mercado, pools e settlement cobertos |
| Resolução CPI | falhas em `lockMarket` | resolução com mock TxLINE no endereço oficial |
| UI | componentes ausentes | mercado, CTA, status API e grade da Copa |
| Replay | módulo ausente | replay rotulado e determinístico |

Último checkpoint local:

- `pnpm audit --audit-level low`: sem vulnerabilidades conhecidas;
- `pnpm typecheck`: passa;
- `pnpm test:coverage`: 8 arquivos, 31 testes, cobertura acima de 80%;
- `pnpm build`: passa;
- API real: `/api/txline/status` retorna `connected:true`;
- Copa: `/api/txline/fixtures` retorna `total=32` e `liveCount=2` com credenciais devnet ativadas.

Os testes Anchor rodam em ledger novo com mock TxLINE carregado no endereço oficial exclusivamente no genesis local.

Supply chain: os testes Anchor usam helpers locais para SPL Token, evitando a dependência JavaScript `@solana/spl-token` e removendo a vulnerabilidade transitiva `bigint-buffer@1.1.5`.
