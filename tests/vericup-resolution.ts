import * as anchor from "@coral-xyz/anchor";
import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  TOKEN_PROGRAM_ID
} from "./token-helpers";
import { expect } from "chai";

const TXORACLE_PROGRAM = new anchor.web3.PublicKey(
  "6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J"
);

async function expectFailure(promise: Promise<unknown>): Promise<void> {
  try {
    await promise;
    expect.fail("Expected transaction to fail");
  } catch (error) {
    expect(error).to.be.instanceOf(Error);
  }
}

describe("TxLINE market resolution", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Vericup as any;
  const payer = (provider.wallet as anchor.Wallet).payer;
  const [config] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("config")],
    program.programId
  );
  let nextFixture = 20_000_000;

  function payload(fixtureId: number, home: number, away: number, period = 100) {
    return {
      ts: new anchor.BN(Math.floor(Date.now() / 1000)),
      fixtureSummary: {
        fixtureId: new anchor.BN(fixtureId),
        updateStats: {
          updateCount: 2,
          minTimestamp: new anchor.BN(1),
          maxTimestamp: new anchor.BN(2)
        },
        eventsSubTreeRoot: Array(32).fill(1)
      },
      fixtureProof: [],
      mainTreeProof: [],
      eventStatRoot: Array(32).fill(2),
      stats: [
        { stat: { key: 1, value: home, period }, statProof: [] },
        { stat: { key: 2, value: away, period }, statProof: [] }
      ]
    };
  }

  async function createLockedMarket(): Promise<{
    fixtureId: number;
    market: anchor.web3.PublicKey;
  }> {
    const fixtureId = nextFixture++;
    const fixtureBytes = new anchor.BN(fixtureId).toArrayLike(Buffer, "le", 8);
    const [market] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("market"), fixtureBytes],
      program.programId
    );
    const protocol = await program.account.protocolConfig.fetch(config);
    const playMint = protocol.playMint as anchor.web3.PublicKey;
    const vault = anchor.utils.token.associatedAddress({ mint: playMint, owner: market });

    await program.methods
      .createMarket(
        new anchor.BN(fixtureId),
        new anchor.BN(Math.floor(Date.now() / 1000) + 1)
      )
      .accounts({
        authority: payer.publicKey,
        config,
        playMint,
        market,
        vault,
        tokenProgram: TOKEN_PROGRAM_ID,
        associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
        systemProgram: anchor.web3.SystemProgram.programId
      })
      .rpc();

    for (let attempt = 0; attempt < 10; attempt += 1) {
      try {
        await program.methods.lockMarket().accounts({ market }).rpc();
        return { fixtureId, market };
      } catch (error) {
        if (attempt === 9 || !(error instanceof Error) || !error.message.includes("MarketStillOpen")) {
          throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
    return { fixtureId, market };
  }

  async function resolve(
    market: anchor.web3.PublicKey,
    value: ReturnType<typeof payload>
  ): Promise<void> {
    await program.methods
      .resolveWithTxline(value)
      .accounts({
        market,
        dailyScoresMerkleRoots: payer.publicKey,
        txoracleProgram: TXORACLE_PROGRAM
      })
      .rpc();
  }

  for (const [home, away, expected] of [
    [2, 1, "home"],
    [1, 1, "draw"],
    [0, 3, "away"]
  ] as const) {
    it(`resolves ${home}-${away} as ${expected}`, async () => {
      const { fixtureId, market } = await createLockedMarket();
      await resolve(market, payload(fixtureId, home, away));
      const account = await program.account.market.fetch(market);
      expect(account.resolvedOutcome).to.have.property(expected);
    });
  }

  it("rejects a proof for another fixture", async () => {
    const { fixtureId, market } = await createLockedMarket();
    await expectFailure(resolve(market, payload(fixtureId + 1, 1, 0)));
  });

  it("rejects non-final score leaves", async () => {
    const { fixtureId, market } = await createLockedMarket();
    await expectFailure(resolve(market, payload(fixtureId, 1, 0, 4)));
  });

  it("rejects duplicate resolution", async () => {
    const { fixtureId, market } = await createLockedMarket();
    const proof = payload(fixtureId, 1, 0);
    await resolve(market, proof);
    await expectFailure(resolve(market, proof));
  });
});
