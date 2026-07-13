# Integração TxLINE

IDL oficial 1.5.6 obtida em 12 de julho de 2026 de `txodds/tx-on-chain`, arquivo `examples/devnet/idl/txoracle.json`. Endereço verificado: `6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J`.

## API ativada

O acesso World Cup Free Tier foi ativado em devnet com uma carteira operacional local. Segredos ficam somente em `.env.local` e `.anchor/`, ambos ignorados pelo git.

- API host: `https://txline-dev.txodds.com`
- Competition ID: `72`
- Subscribe tx: `5Bj9S7te1RuRdPhqwqNPQ1PrCwTJWAS8v24ZQaQEF3T5sQ16mUF8KrLgGAfrNC91BU6FBj1QJ2EVnH8VGC4tky1a`
- Fixture snapshot testado: `GET /api/fixtures/snapshot?competitionId=72`
- Score snapshot testado: `GET /api/scores/snapshot/18175981`
- Proof testado: `GET /api/scores/stat-validation?fixtureId=18175981&seq=991&statKeys=1,2`

O app expõe `/api/txline/status`, `/api/txline/fixtures` e `/api/txline/scores/[fixtureId]` como proxies server-side para não vazar credenciais.

## Cobertura da Copa

A interface usa os 32 jogos confirmados no Schedule oficial da TxLINE e faz merge com o snapshot vivo de fixtures para `competitionId=72`. Em 13 de julho de 2026, o endpoint devnet retornou 2 fixtures frescas de semifinal e a UI manteve 32 jogos disponíveis para teste/replay.

## Prova on-chain

O `TxlineClient` normaliza casing, aceita somente `game_finalised` com status/período final, exige hashes de 32 bytes e preserva a ordem entre stats e provas. O keeper busca `statKeys=1,2`.

No programa, `resolve_with_txline`:

1. exige mercado LOCKED e fixture correspondente;
2. exige exatamente as chaves 1 e 2, nessa ordem;
3. cria dois predicados `EqualTo` a partir dos próprios valores das folhas;
4. chama `validateStatV2` no endereço oficial;
5. valida program ID, retorno Borsh booleano e resultado verdadeiro;
6. deriva o outcome e grava hash Keccak, slot e estado RESOLVED.

O mock local compartilha o discriminator e o formato de argumentos, mas só é carregado por `[[test.genesis]]`. Ele não é aceito como programa alternativo em devnet.

## Pendência honesta

A API TxLINE real está ativada e testada. O próximo incremento para uma demo ainda mais forte é publicar uma resolução VeriCup em devnet com Explorer links de market, resolve e claim.
