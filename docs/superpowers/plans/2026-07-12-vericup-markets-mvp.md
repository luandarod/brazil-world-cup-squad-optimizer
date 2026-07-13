# VeriCup Markets MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a World Cup prediction market where judges can register a guest prediction without a wallet, while the final outcome is computed from a TxLINE `game_finalised` score proof and can be proven through an on-chain CPI.

**Architecture:** A pnpm workspace contains a Next.js application, a small shared TxLINE client, and an automatic keeper. The primary fan path uses walletless guest predictions and virtual PLAY. An Anchor 0.32.1 proof layer owns PLAY-token vaults, validates final score stats through TxLINE `validateStatV2`, resolves HOME/DRAW/AWAY deterministically, and pays claims for technical verification. Local tests use a compatible mock validation program; the submission gate uses TxLINE's real devnet program and IDL.

**Tech Stack:** Node.js 24, pnpm 11, TypeScript 5.9, Next.js 16, React 19, Vitest 4, Playwright 1.61, Anchor 0.32.1, Rust, Solana CLI 2.3.0, `@solana/web3.js` 1.98, local SPL Token test helpers, Zod 4, TxLINE devnet API and program `6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J`.

---

## Delivery Order and Gates

The MVP is implemented in this order because each stage produces a usable, testable boundary:

1. workspace and pinned toolchain;
2. TxLINE parsing and proof mapping;
3. deterministic keeper decisions;
4. protocol, faucet, market, and deposits;
5. TxLINE CPI resolution;
6. claims and refunds;
7. web experience;
8. replay, devnet proof, deployment, and submission documentation;
9. lean-code pass and full verification.

Do not start a later task while its predecessor has failing checks. Do not use real-value assets or the TxLINE credit mint as a market asset.

### Task 1: Bootstrap the pinned workspace and toolchain

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `tsconfig.base.json`
- Create: `vitest.config.ts`
- Create: `rust-toolchain.toml`
- Create: `Anchor.toml`
- Create: `Cargo.toml`
- Create: `programs/vericup/Cargo.toml`
- Create: `programs/vericup/src/lib.rs`
- Vendor: `idls/txoracle.json`

- [ ] **Step 1: Verify or install the WSL toolchain**

Use Ubuntu WSL because the host does not currently expose Rust, Solana, or Anchor. Review the official installers before execution, then install the versions recommended for Anchor 0.32.1:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o /tmp/rustup-init.sh
sha256sum /tmp/rustup-init.sh
sh /tmp/rustup-init.sh -y
. "$HOME/.cargo/env"
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev libudev-dev
sh -c "$(curl -sSfL https://release.anza.xyz/v2.3.0/install)"
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"
cargo install --git https://github.com/solana-foundation/anchor avm --force
avm install 0.32.1 --from-source
avm use 0.32.1
```

Run inside WSL:

```bash
rustc --version
solana --version
anchor --version
node --version
```

Expected: Rust is installed, `solana-cli 2.3.0`, `anchor-cli 0.32.1`, and Node is at least 20.

- [ ] **Step 2: Add workspace configuration**

Write `package.json`:

```json
{
  "name": "vericup-markets",
  "private": true,
  "packageManager": "pnpm@11.7.0",
  "scripts": {
    "build": "pnpm --filter @vericup/txline build && pnpm --filter @vericup/keeper build && pnpm --filter @vericup/app build",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck",
    "test": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:program": "anchor test",
    "test:e2e": "pnpm --filter @vericup/app test:e2e"
  },
  "devDependencies": {
    "@vitest/coverage-v8": "4.1.10",
    "typescript": "5.9.3",
    "vitest": "4.1.10"
  }
}
```

Write `pnpm-workspace.yaml`:

```yaml
packages:
  - app
  - keeper
  - packages/*
```

Write `rust-toolchain.toml`:

```toml
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy"]
profile = "minimal"
```

Write root `Cargo.toml`:

```toml
[workspace]
members = ["programs/*"]
resolver = "2"

[profile.release]
overflow-checks = true
lto = "fat"
codegen-units = 1
```

Write `programs/vericup/Cargo.toml`:

```toml
[package]
name = "vericup"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "lib"]
name = "vericup"

[features]
default = []
cpi = ["no-entrypoint"]
no-entrypoint = []
no-idl = []
no-log-ix-name = []
idl-build = ["anchor-lang/idl-build", "anchor-spl/idl-build"]

[dependencies]
anchor-lang = "0.32.1"
anchor-spl = "0.32.1"
```

Write the initial compile-only `programs/vericup/src/lib.rs`:

```rust
use anchor_lang::prelude::*;

declare_id!("11111111111111111111111111111111");

#[program]
pub mod vericup {}
```

- [ ] **Step 3: Vendor the official devnet IDL with provenance**

Download exactly:

```bash
curl -fsSL https://raw.githubusercontent.com/txodds/tx-on-chain/main/examples/devnet/idl/txoracle.json -o idls/txoracle.json
```

Verify:

```bash
node -e "const i=require('./idls/txoracle.json'); if(i.address!=='6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J'||i.metadata.version!=='1.5.6') process.exit(1)"
```

Expected: exit 0. Record the upstream URL and retrieval date in `docs/txline-integration.md` during Task 8.

- [ ] **Step 4: Install JavaScript dependencies and verify clean bootstrap**

Run:

```bash
pnpm install
cargo update -p blake3 --precise 1.8.2
cargo update -p borsh@1.7.0 --precise 1.5.7
cargo update -p proc-macro-crate@3.5.0 --precise 3.1.0
cargo update -p indexmap@2.14.0 --precise 2.10.0
cargo update -p zeroize@1.9.0 --precise 1.8.1
cargo update -p zeroize_derive@1.5.0 --precise 1.4.2
cargo update -p unicode-segmentation@1.13.3 --precise 1.10.1
pnpm exec vitest run --passWithNoTests
anchor build
```

The Cargo pins mirror versions compatible with the Rust 1.84 compiler bundled in Solana 2.3.0 and prevent newer Edition 2024 transitive releases from breaking SBF builds. On WSL repositories mounted under `/mnt/c`, set `CARGO_TARGET_DIR` to a Linux path for `anchor idl build`, then copy only the generated IDL into `target/idl/`; this avoids P9 filesystem stalls.

Expected: dependency installation succeeds, Vitest reports no tests without failure, Anchor produces `target/deploy/vericup.so`, and the generated IDL address matches the program keypair public key.

- [ ] **Step 5: Commit the bootstrap**

```bash
git add .gitignore .env.example package.json pnpm-workspace.yaml tsconfig.base.json vitest.config.ts rust-toolchain.toml Anchor.toml Cargo.toml programs idls pnpm-lock.yaml
git commit -m "build: bootstrap VeriCup workspace"
```

### Task 2: Build the TxLINE boundary with schema validation

**Files:**
- Create: `packages/txline/package.json`
- Create: `packages/txline/tsconfig.json`
- Create: `packages/txline/src/index.test.ts`
- Create: `packages/txline/src/index.ts`

- [ ] **Step 1: Write failing parser tests**

Create tests covering the actual casing variations documented by TxLINE:

```ts
import { describe, expect, it } from "vitest";
import { finalScoreSchema, mapValidationPayload, scoreOutcome } from "./index";

describe("TxLINE score parsing", () => {
  it("accepts a finalised record and normalises casing", () => {
    const score = finalScoreSchema.parse({
      FixtureId: 18175981,
      Seq: 991,
      action: "game_finalised",
      statusId: 100,
      period: 100,
      participant1Score: 2,
      participant2Score: 1,
    });
    expect(score).toMatchObject({ fixtureId: 18175981, seq: 991, home: 2, away: 1 });
  });

  it("rejects an in-play record", () => {
    expect(() => finalScoreSchema.parse({
      fixtureId: 1, seq: 3, action: "score_changed", statusId: 4,
      period: 4, participant1Score: 1, participant2Score: 0,
    })).toThrow();
  });

  it.each([[2, 1, "HOME"], [1, 1, "DRAW"], [0, 2, "AWAY"]] as const)(
    "maps %i-%i to %s", (home, away, outcome) => {
      expect(scoreOutcome(home, away)).toBe(outcome);
    },
  );
});

describe("TxLINE proof mapping", () => {
  it("rejects proof hashes that are not 32 bytes", () => {
    expect(() => mapValidationPayload({
      summary: { fixtureId: 1, updateStats: { updateCount: 1, minTimestamp: 1, maxTimestamp: 1 }, eventStatsSubTreeRoot: "AA==" },
      subTreeProof: [], mainTreeProof: [], eventStatRoot: "AA==", statsToProve: [], statProofs: [],
    })).toThrow("Expected 32 bytes");
  });
});
```

- [ ] **Step 2: Run the RED gate**

Run:

```bash
pnpm vitest run packages/txline/src/index.test.ts
```

Expected: FAIL because `./index` does not exist.

- [ ] **Step 3: Implement the minimal public API**

`packages/txline/src/index.ts` must export:

```ts
export type Outcome = "HOME" | "DRAW" | "AWAY";
export const finalScoreSchema: z.ZodType<FinalScore>;
export function scoreOutcome(home: number, away: number): Outcome;
export function bytes32(value: string | number[] | Uint8Array): number[];
export function mapValidationPayload(value: unknown): StatValidationPayload;
export class TxlineClient {
  constructor(config: { origin: string; jwt: string; apiToken: string; fetch?: typeof fetch });
  scoreSnapshot(fixtureId: number): Promise<unknown>;
  scoreValidation(fixtureId: number, seq: number): Promise<StatValidationPayload>;
}
```

Implementation requirements:

- use Zod transforms to accept `FixtureId`/`fixtureId` and `Seq`/`seq`;
- require `action === "game_finalised"`, `statusId === 100`, and `period === 100`;
- request `/api/scores/stat-validation` with `statKeys=1,2`;
- send both `Authorization: Bearer` and `X-Api-Token` headers;
- decode base64, hex, byte-array, and `Uint8Array` hashes to exactly 32 bytes;
- map `statsToProve[index]` to `statProofs[index]` without reordering.

- [ ] **Step 4: Run GREEN and coverage**

```bash
pnpm vitest run packages/txline/src/index.test.ts
pnpm vitest run packages/txline/src/index.test.ts --coverage
```

Expected: all TxLINE tests pass and the package has at least 80% line, function, statement, and branch coverage.

- [ ] **Step 5: Commit the TxLINE boundary**

```bash
git add packages/txline pnpm-lock.yaml
git commit -m "feat: add validated TxLINE client"
```

### Task 3: Implement deterministic keeper decisions and SSE recovery

**Files:**
- Create: `keeper/package.json`
- Create: `keeper/tsconfig.json`
- Create: `keeper/src/lifecycle.test.ts`
- Create: `keeper/src/lifecycle.ts`
- Create: `keeper/src/worker.ts`

- [ ] **Step 1: Write failing lifecycle tests**

```ts
import { describe, expect, it } from "vitest";
import { decideMarketAction, eventKey, reconnectDelay } from "./lifecycle";

describe("keeper lifecycle", () => {
  it("locks an open market at kickoff", () => {
    expect(decideMarketAction({ state: "OPEN", kickoff: 100, now: 100 })).toBe("LOCK");
  });

  it("resolves only a locked market with a final score", () => {
    expect(decideMarketAction({ state: "LOCKED", kickoff: 100, now: 110, finalScore: true })).toBe("RESOLVE");
    expect(decideMarketAction({ state: "OPEN", kickoff: 100, now: 110, finalScore: true })).toBe("LOCK");
  });

  it("deduplicates by fixture and sequence", () => {
    expect(eventKey({ fixtureId: 42, seq: 7 })).toBe("42:7");
  });

  it("caps reconnect delay at thirty seconds", () => {
    expect(reconnectDelay(20)).toBe(30_000);
  });
});
```

- [ ] **Step 2: Run RED**

```bash
pnpm vitest run keeper/src/lifecycle.test.ts
```

Expected: FAIL because the lifecycle module does not exist.

- [ ] **Step 3: Implement pure decisions before network effects**

`keeper/src/lifecycle.ts` exports only:

```ts
export type MarketState = "OPEN" | "LOCKED" | "RESOLVED";
export type KeeperAction = "NONE" | "LOCK" | "RESOLVE";

export function decideMarketAction(input: {
  state: MarketState;
  kickoff: number;
  now: number;
  finalScore?: boolean;
}): KeeperAction;

export function eventKey(event: { fixtureId: number; seq: number }): string;
export function reconnectDelay(attempt: number): number;
```

Use `Math.min(30_000, 1_000 * 2 ** attempt)` for retry delay. `worker.ts` composes this with `TxlineClient`, an injected Anchor gateway, and an in-memory bounded set of the last 1,000 event keys. A `401` refreshes the guest JWT through an injected credential provider; other HTTP failures reconnect without discarding the activated API token.

- [ ] **Step 4: Run GREEN and commit**

```bash
pnpm vitest run keeper/src/lifecycle.test.ts
pnpm --filter @vericup/keeper typecheck
git add keeper
git commit -m "feat: add automatic market keeper"
```

### Task 4: Implement protocol initialization, PLAY faucet, market creation, and deposits

**Files:**
- Modify: `programs/vericup/src/lib.rs`
- Create: `tests/vericup-market.ts`

- [ ] **Step 1: Write failing Anchor tests**

The test creates a six-decimal SPL mint whose authority is the protocol PDA, then verifies:

```ts
it("mints PLAY only once per wallet", async () => {
  await program.methods.claimDemoTokens().accounts(faucetAccounts).rpc();
  expect(Number((await getAccount(connection, userAta)).amount)).toBe(1_000_000_000);
  await expect(program.methods.claimDemoTokens().accounts(faucetAccounts).rpc()).to.be.rejected;
});

it("creates one market per fixture and records the configured mint", async () => {
  await program.methods.createMarket(new BN(18175981), new BN(kickoff)).accounts(createAccounts).rpc();
  const market = await program.account.market.fetch(marketPda);
  expect(market.fixtureId.toNumber()).to.equal(18175981);
  expect(market.playMint.equals(playMint)).to.equal(true);
});

it("takes HOME, DRAW, and AWAY positions before kickoff", async () => {
  await takePosition("home", 100_000_000);
  await takePosition("draw", 50_000_000);
  await takePosition("away", 25_000_000);
  const market = await program.account.market.fetch(marketPda);
  expect(market.pools.map((v: BN) => v.toNumber())).to.deep.equal([100_000_000, 50_000_000, 25_000_000]);
});

it("rejects deposits at or after kickoff", async () => {
  await moveClockPastKickoff();
  await expect(takePosition("home", 1)).to.be.rejected;
});
```

- [ ] **Step 2: Run RED**

```bash
anchor test --skip-build tests/vericup-market.ts
```

Expected: FAIL because protocol accounts and instructions are absent.

- [ ] **Step 3: Implement minimal accounts and instructions**

Use these state contracts:

```rust
#[account]
pub struct ProtocolConfig {
    pub authority: Pubkey,
    pub play_mint: Pubkey,
    pub bump: u8,
}

#[account]
pub struct Market {
    pub fixture_id: i64,
    pub kickoff: i64,
    pub play_mint: Pubkey,
    pub vault: Pubkey,
    pub state: MarketState,
    pub pools: [u64; 3],
    pub resolved_outcome: Option<Outcome>,
    pub proof_hash: [u8; 32],
    pub resolution_slot: u64,
    pub claimed_winning_stake: u64,
    pub claimed_payout: u64,
    pub bump: u8,
}

#[account]
pub struct Position {
    pub owner: Pubkey,
    pub market: Pubkey,
    pub outcome: Outcome,
    pub amount: u64,
    pub claimed: bool,
    pub bump: u8,
}
```

Implement `initialize_protocol`, `claim_demo_tokens`, `create_market`, `take_position`, and `lock_market`. Required invariants:

- config seed: `b"config"`;
- market seed: `b"market"` plus `fixture_id.to_le_bytes()`;
- position seed: `b"position"`, market key, owner key, and outcome byte;
- faucet receipt seed: `b"faucet"`, config key, and wallet key;
- faucet amount: `1_000 * 10^6` base units;
- `take_position` independently checks `Clock::get()?.unix_timestamp < kickoff` and state `OPEN`;
- all additions use `checked_add`;
- all transfers use `anchor_spl::token_interface` and the configured mint.

- [ ] **Step 4: Run GREEN and regression suite**

```bash
anchor test tests/vericup-market.ts
pnpm test
```

Expected: market tests and all TypeScript unit tests pass.

- [ ] **Step 5: Commit**

```bash
git add programs/vericup tests/vericup-market.ts
git commit -m "feat: add demo market and PLAY pools"
```

### Task 5: Resolve markets through TxLINE `validateStatV2`

**Files:**
- Modify: `programs/vericup/src/lib.rs`
- Create: `programs/mock-txoracle/Cargo.toml`
- Create: `programs/mock-txoracle/src/lib.rs`
- Create: `tests/vericup-resolution.ts`
- Modify: `Anchor.toml`

- [ ] **Step 1: Create a compatible local validation mock**

The mock exposes the TxLINE `validate_stat_v2` discriminator and account shape and returns a boolean. It verifies only whether its test root account contains the expected fixture, stats, and period. The mock is deployed exclusively under `[test.validator]`; it is never accepted by the devnet deployment because VeriCup constrains the oracle program address to the official TxLINE devnet ID.

- [ ] **Step 2: Write failing resolution tests**

```ts
it.each([
  [2, 1, "home"],
  [1, 1, "draw"],
  [0, 3, "away"],
] as const)("resolves %i-%i as %s", async (home, away, expected) => {
  const payload = finalPayload({ fixtureId, home, away, period: 100 });
  await program.methods.resolveWithTxline(payload).accounts(resolveAccounts).rpc();
  const market = await program.account.market.fetch(marketPda);
  expect(market.resolvedOutcome).to.have.property(expected);
});

it("rejects a proof for another fixture", async () => {
  const payload = finalPayload({ fixtureId: fixtureId + 1, home: 1, away: 0, period: 100 });
  await expect(program.methods.resolveWithTxline(payload).accounts(resolveAccounts).rpc()).to.be.rejected;
});

it("rejects non-final score leaves", async () => {
  const payload = finalPayload({ fixtureId, home: 1, away: 0, period: 4 });
  await expect(program.methods.resolveWithTxline(payload).accounts(resolveAccounts).rpc()).to.be.rejected;
});

it("rejects duplicate resolution", async () => {
  await resolveFinal(1, 0);
  await expect(resolveFinal(1, 0)).to.be.rejected;
});
```

- [ ] **Step 3: Run RED**

```bash
anchor test tests/vericup-resolution.ts
```

Expected: FAIL because `resolve_with_txline` is absent.

- [ ] **Step 4: Implement a constrained CPI**

Use Anchor's IDL-generated external program interface:

```rust
declare_program!(txoracle);
use txoracle::types::{Comparison, NDimensionalStrategy, StatPredicate, TraderPredicate};
```

`resolve_with_txline` must:

1. require `market.state == LOCKED`;
2. require `payload.fixture_summary.fixture_id == market.fixture_id`;
3. require exactly two leaves with keys `1` and `2` in that order;
4. require both score leaves have `period == 100`;
5. construct two on-chain `EqualTo` predicates from the submitted leaf values, covering each stat exactly once;
6. CPI to the official TxLINE program account passed under an address constraint;
7. read CPI return data and require the returning program is TxLINE and the Borsh boolean is `true`;
8. calculate HOME/DRAW/AWAY by comparing the two verified values;
9. store `hash(payload.try_to_vec())`, the current slot, immutable outcome, and state `RESOLVED`.

Never accept an outcome or predicate from the keeper.

- [ ] **Step 5: Run GREEN and inspect compute use**

```bash
anchor test tests/vericup-resolution.ts
anchor test
```

Expected: all outcome and rejection tests pass. Capture transaction logs and ensure the caller sets a compute-unit limit no higher than 1,400,000.

- [ ] **Step 6: Commit**

```bash
git add programs tests Anchor.toml
git commit -m "feat: resolve markets with TxLINE proofs"
```

### Task 6: Implement deterministic claims and no-winner refunds

**Files:**
- Modify: `programs/vericup/src/lib.rs`
- Create: `tests/vericup-settlement.ts`

- [ ] **Step 1: Write failing payout tests**

```ts
it("pays winners proportionally", async () => {
  await deposit(alice, "home", 60);
  await deposit(bob, "home", 40);
  await deposit(carol, "away", 100);
  await resolveFinal(2, 0);
  expect(await claimDelta(alice, "home")).to.equal(120);
  expect(await claimDelta(bob, "home")).to.equal(80);
});

it("assigns integer remainder to the final winning claim", async () => {
  await deposit(alice, "draw", 1);
  await deposit(bob, "draw", 2);
  await deposit(carol, "home", 7);
  await resolveFinal(1, 1);
  await claim(alice, "draw");
  const finalDelta = await claimDelta(bob, "draw");
  expect(await vaultBalance()).to.equal(0);
  expect(finalDelta).to.equal(7);
});

it("refunds deposits when nobody selected the winner", async () => {
  await deposit(alice, "home", 50);
  await resolveFinal(0, 1);
  expect(await refundDelta(alice, "home")).to.equal(50);
});

it("rejects duplicate claims", async () => {
  await claim(alice, "home");
  await expect(claim(alice, "home")).to.be.rejected;
});
```

- [ ] **Step 2: Run RED**

```bash
anchor test tests/vericup-settlement.ts
```

Expected: FAIL because claim/refund instructions are absent.

- [ ] **Step 3: Implement checked payout rules**

Normal payout:

```rust
let total_pool = market.pools.iter().try_fold(0u64, |sum, value| sum.checked_add(*value)).ok_or(ErrorCode::Overflow)?;
let winner_pool = market.pools[usize::from(winner)];
let is_last = market.claimed_winning_stake.checked_add(position.amount).ok_or(ErrorCode::Overflow)? == winner_pool;
let payout = if is_last {
    total_pool.checked_sub(market.claimed_payout).ok_or(ErrorCode::Overflow)?
} else {
    u64::try_from((u128::from(position.amount) * u128::from(total_pool)) / u128::from(winner_pool))
        .map_err(|_| ErrorCode::Overflow)?
};
```

`refund` is available only when `winner_pool == 0` and returns the caller's original position amount. Both paths mark the position claimed before the token transfer and sign with the market PDA.

- [ ] **Step 4: Run GREEN and commit**

```bash
anchor test tests/vericup-settlement.ts
anchor test
git add programs/vericup tests/vericup-settlement.ts
git commit -m "feat: add deterministic settlement payouts"
```

### Task 7: Build the judge-facing Next.js experience

**Files:**
- Create: `app/package.json`
- Create: `app/next.config.ts`
- Create: `app/tsconfig.json`
- Create: `app/src/app/layout.tsx`
- Create: `app/src/app/page.tsx`
- Create: `app/src/app/globals.css`
- Create: `app/src/components/market-card.test.tsx`
- Create: `app/src/components/market-card.tsx`
- Create: `app/src/components/proof-receipt.test.tsx`
- Create: `app/src/components/proof-receipt.tsx`
- Create: `app/src/lib/program.ts`
- Create: `app/src/app/api/txline/fixtures/route.ts`
- Create: `app/src/app/api/txline/scores/[fixtureId]/route.ts`
- Create: `app/playwright.config.ts`

- [ ] **Step 1: Write failing component tests**

```tsx
it("shows TxLINE freshness and all three market outcomes", () => {
  render(<MarketCard market={openMarketFixture} />);
  expect(screen.getByText("Powered and settled by TxLINE")).toBeVisible();
  expect(screen.getByRole("button", { name: /Brazil/i })).toBeEnabled();
  expect(screen.getByRole("button", { name: /Draw/i })).toBeEnabled();
  expect(screen.getByRole("button", { name: /France/i })).toBeEnabled();
  expect(screen.getByText(/updated 12 seconds ago/i)).toBeVisible();
});

it("renders an auditable resolution receipt", () => {
  render(<ProofReceipt receipt={resolvedReceiptFixture} />);
  expect(screen.getByText("TxLINE proof verified")).toBeVisible();
  expect(screen.getByText("18175981")).toBeVisible();
  expect(screen.getByRole("link", { name: "View resolution on Solana Explorer" })).toHaveAttribute("href", expect.stringContaining("cluster=devnet"));
});
```

- [ ] **Step 2: Run RED**

```bash
pnpm vitest run app/src/components
```

Expected: FAIL because the components do not exist.

- [ ] **Step 3: Implement the smallest complete interface**

The page contains exactly:

- concise hero explaining verifiable settlement;
- network and feed-health badge;
- one featured market card with fixture, kickoff, TxLINE StablePrice, and virtual pool distribution;
- guest prediction action that does not require a wallet;
- HOME/DRAW/AWAY position actions;
- live or replay score status;
- settlement safety checklist;
- proof receipt and claim/refund action.

Server routes import `@vericup/txline` and read credentials from `TXLINE_GUEST_JWT` and `TXLINE_API_TOKEN`. They return a controlled `503` with `lastUpdated` when upstream is unavailable and never serialize credentials. Any Solana transaction lives in proof mode and uses an operator wallet, not a required fan wallet.

- [ ] **Step 4: Run GREEN, accessibility checks, typecheck, and build**

```bash
pnpm vitest run app/src/components
pnpm --filter @vericup/app typecheck
pnpm --filter @vericup/app lint
pnpm --filter @vericup/app build
```

Expected: tests pass, no type or lint errors, and Next.js completes a production build.

- [ ] **Step 5: Commit**

```bash
git add app pnpm-lock.yaml
git commit -m "feat: add VeriCup market experience"
```

### Task 8: Add verified replay, E2E coverage, devnet deployment, and docs

**Files:**
- Create: `keeper/src/replay.test.ts`
- Create: `keeper/src/replay.ts`
- Create: `app/e2e/judge-flow.spec.ts`
- Create: `scripts/subscribe-txline-devnet.ts`
- Create: `scripts/deploy-devnet.ts`
- Create: `README.md`
- Create: `docs/txline-integration.md`
- Create: `docs/demo-script.md`
- Create: `docs/testing/vericup-mvp.tdd.md`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write failing replay and E2E tests**

Replay unit test:

```ts
it("labels historical events and preserves fixture sequence", () => {
  const replay = replayEvent({ fixtureId: 18175981, seq: 991, action: "game_finalised" });
  expect(replay).toEqual(expect.objectContaining({ mode: "REPLAY", fixtureId: 18175981, seq: 991 }));
});
```

Playwright judge flow:

```ts
test("judge can inspect the complete verified settlement journey", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("VeriCup Markets")).toBeVisible();
  await expect(page.getByText("Powered and settled by TxLINE")).toBeVisible();
  await page.getByRole("button", { name: "Run verified replay" }).click();
  await expect(page.getByText("Historical replay")).toBeVisible();
  await expect(page.getByText("TxLINE proof verified")).toBeVisible();
  await expect(page.getByRole("link", { name: "View resolution on Solana Explorer" })).toBeVisible();
});
```

- [ ] **Step 2: Run RED**

```bash
pnpm vitest run keeper/src/replay.test.ts
pnpm --filter @vericup/app test:e2e -- --grep "judge can inspect"
```

Expected: both targets fail because replay behavior is absent.

- [ ] **Step 3: Implement replay without a second settlement path**

`replay.ts` may select and pace historical events, but must pass the observed fixture ID, sequence, final score, and proof through the same `TxlineClient.scoreValidation`, keeper `RESOLVE` decision, and Anchor `resolveWithTxline` transaction used in live mode. The UI label is driven by `mode: "REPLAY"`; no fake proof or local outcome is accepted.

- [ ] **Step 4: Activate the TxLINE devnet free tier**

Run the repository script with one funded operator devnet wallet. This is required for TxLINE activation and proof mode, not for the fan-facing guest prediction flow. It must:

1. subscribe to service level `1` for four weeks with empty selected leagues;
2. obtain a guest JWT from `https://txline-dev.txodds.com/auth/guest/start`;
3. sign `${txSig}::${jwt}` with the subscribing wallet;
4. activate through `https://txline-dev.txodds.com/api/token/activate`;
5. store tokens only in local ignored environment files.

Verify a proof request for a real observed `game_finalised` sequence with `statKeys=1,2` before deployment.

- [ ] **Step 5: Deploy and verify the real CPI**

Inside WSL:

```bash
solana config set --url devnet
anchor build
anchor deploy --provider.cluster devnet
pnpm tsx scripts/deploy-devnet.ts
```

Run one complete devnet transaction against official TxLINE program `6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J`. Record the VeriCup program ID, market address, resolution signature, claim signature, fixture ID, and sequence in `docs/txline-integration.md`.

- [ ] **Step 6: Complete documentation and TDD evidence**

`README.md` includes setup, devnet addresses, architecture, exact commands, judge walkthrough, no-real-value disclaimer, and TxLINE endpoints:

- `POST /auth/guest/start`;
- `POST /api/token/activate`;
- `GET /api/scores/snapshot/{fixtureId}`;
- `GET /api/scores/stat-validation?fixtureId=...&seq=...&statKeys=1,2`;
- `GET /api/scores/stream`;
- fixtures and StablePrice endpoints confirmed during implementation.

`docs/demo-script.md` budgets the five-minute video: 30 seconds problem, 45 seconds product, 150 seconds end-to-end flow, 45 seconds proof/Explorer, 20 seconds tests, and 10 seconds TxLINE feedback.

`docs/testing/vericup-mvp.tdd.md` records each RED command/output, matching GREEN command/output, coverage, known gaps, and checkpoint commits.

- [ ] **Step 7: Run GREEN and commit**

```bash
pnpm vitest run keeper/src/replay.test.ts
pnpm --filter @vericup/app test:e2e
git add keeper app scripts README.md docs .github
git commit -m "feat: deliver verified replay and judge workflow"
```

### Task 9: Run lean-code-pass and full verification

**Files:**
- Modify only files changed by Tasks 1-8 when simplification preserves behavior.
- Update: `docs/testing/vericup-mvp.tdd.md`

- [ ] **Step 1: Inspect the current task diff and remove overbuilding**

Run:

```bash
git diff 0adeb27..HEAD --stat
git diff 0adeb27..HEAD --name-only
```

Apply `lean-code-pass` to the changed code. Specifically inspect for one-call wrappers, duplicated PDA helpers, unnecessary configuration, components with no independent behavior, repeated proof mapping, comments that restate code, and files that are easier to understand merged. Do not simplify the CPI boundary, checked arithmetic, credential isolation, replay labeling, or on-chain invariant checks.

- [ ] **Step 2: Run the complete fresh verification gate**

```bash
pnpm lint
pnpm typecheck
pnpm test:coverage
pnpm build
anchor build
anchor test
pnpm test:e2e
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
pnpm audit --audit-level high
git diff --check
git status --short
```

Expected:

- all commands exit 0;
- no skipped tests;
- new TypeScript code meets at least 80% coverage;
- Anchor program tests cover every instruction and rejection path;
- no high-severity dependency advisory remains unexplained;
- only intentional tracked changes remain.

- [ ] **Step 3: Perform targeted secret and asset scans**

```bash
rg -n --hidden --glob '!pnpm-lock.yaml' --glob '!target/**' '(TXLINE_API_TOKEN=.+|TXLINE_GUEST_JWT=.+|\[[0-9]{20,}(,[0-9]{1,3})+\])' .
rg -n 'TXLINE_MINT|4Zao8ocPhmMgq7PdsYWyxvqySMGx7xb9cMftPMkEokRG' programs app keeper
```

Expected: the first command finds no secrets; the second finds TxLINE mint only in subscription/auth documentation or configuration, never as the PLAY asset or pool mint.

- [ ] **Step 4: Re-run the real judge path**

Using the deployed site as a fresh judge:

1. register a guest prediction without connecting a wallet;
2. run the clearly labeled replay;
3. observe TxLINE-backed resolution;
4. inspect the demo proof receipt;
5. run the optional operator-wallet proof path;
6. open the Explorer links produced by proof mode;
7. follow the README from a fresh checkout.

Record fresh signatures and screenshots for the demo, but do not commit wallet keys or API tokens.

- [ ] **Step 5: Commit the verified lean pass**

```bash
git add -A
git commit -m "refactor: simplify and verify VeriCup MVP"
git log --oneline --decorate -12
```

Expected: checkpoint history preserves RED tests, GREEN implementations, replay delivery, and the final verified simplification.

## Final Submission Checklist

- [ ] Public repository was created specifically for this hackathon.
- [ ] Deployed frontend link works without private judge credentials.
- [ ] Anchor program, market, resolution, and claim addresses are documented.
- [ ] TxLINE is the primary fixture, odds, score, and validation source.
- [ ] Demo video is five minutes or less and shows the real core flow.
- [ ] API feedback names both strengths and concrete friction.
- [ ] Global submission is complete by July 18 for the safer Brazil deadline.
- [ ] The identical project is also submitted to the Superteam Brasil listing.
