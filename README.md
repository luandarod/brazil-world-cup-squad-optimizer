# VeriCup Markets

Prediction markets da Copa com entrada sem carteira para torcedores e settlement verificável por TxLINE. O caminho principal registra palpites convidados com PLAY virtual; a camada Solana fica como prova opcional para demonstrar que o resultado foi derivado de dados TxLINE, não escolhido pelo backend.

## Por que esta submissão é diferente

- UX principal sem wallet, adequada para judges testarem em segundos;
- grade com 32 jogos confirmados da Copa, incluindo snapshot vivo TxLINE para `competitionId=72`;
- score final consumido via TxLINE snapshot/SSE e normalizado pelo keeper;
- prova opcional validada pelo programa oficial `6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J`;
- fixture, chaves de stat `1` e `2`, ordem e período final validados no modo de prova;
- PLAY é pontuação virtual de demonstração, sem valor real.

## Arquitetura

```text
Fan UI sem carteira -> guest prediction -> PLAY virtual
TxLINE fixtures/scores/proofs -> keeper -> resultado determinístico
TxLINE stat-validation -> resolve_with_txline -> CPI validateStatV2 opcional
Anchor vault -> claim_payout ou refund_position no modo de prova
```

## Desenvolvimento

Requisitos: Node 24, pnpm 11.7, Rust, Solana 2.3 e Anchor 0.32.1.

```bash
pnpm install
pnpm test
pnpm typecheck
pnpm build
anchor build
anchor test
```

Copie `.env.example` para `.env.local`. Tokens TxLINE ficam somente no servidor e nunca usam prefixo `NEXT_PUBLIC_`.

## Endpoints TxLINE usados

- `POST /auth/guest/start`
- `POST /api/token/activate`
- `GET /api/fixtures/snapshot?competitionId=72`
- `GET /api/scores/snapshot/{fixtureId}`
- `GET /api/scores/stat-validation?fixtureId=...&seq=...&statKeys=1,2`

## Carteiras e endereços

- Usuário final: nenhuma carteira necessária no fluxo principal.
- Operador: uma carteira Solana devnet foi usada para ativar o acesso gratuito da TxLINE.
- TxLINE devnet oracle: `6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J`
- TxLINE World Cup competition: `72`
- VeriCup program local/devnet target: `BgJSdxW7zKzg5r5sctQoxEbc73pEeiaFGj3ebqvR8gnd`

O token TxLINE e a chave operacional ficam em arquivos ignorados pelo git. O app publicado deve receber `TXLINE_ORIGIN`, `TXLINE_GUEST_JWT` e `TXLINE_API_TOKEN` como variáveis de ambiente server-side.

## Caminho do jurado

1. Abra a UI e confirme o selo `TxLINE conectada`.
2. Veja a grade da Copa com os 32 jogos confirmados e os jogos frescos do snapshot TxLINE.
3. Registre um palpite HOME, DRAW ou AWAY sem conectar carteira.
4. Confira o recibo de prova e os endpoints usados para settlement.
5. Para avaliação técnica, rode a prova Anchor local ou em devnet com uma carteira operacional.

Veja [integração TxLINE](docs/txline-integration.md) e [roteiro de demo](docs/demo-script.md).
