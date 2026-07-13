import * as anchor from "@coral-xyz/anchor";
import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  TOKEN_PROGRAM_ID,
  getAccount,
  getOrCreateAssociatedTokenAccount
} from "./token-helpers";
import { expect } from "chai";

const TXORACLE_PROGRAM = new anchor.web3.PublicKey(
  "6pW64gN1s2uqjHkn1unFeEjAwJkPGHoppGvS715wyP2J"
);

type OutcomeName = "home" | "draw" | "away";
type TestUser = {
  signer: anchor.web3.Keypair;
  tokenAccount: anchor.web3.PublicKey;
};

async function expectFailure(promise: Promise<unknown>): Promise<void> {
  try {
    await promise;
    expect.fail("Expected transaction to fail");
  } catch (error) {
    expect(error).to.be.instanceOf(Error);
  }
}

describe("deterministic market settlement", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Vericup as any;
  const payer = (provider.wallet as anchor.Wallet).payer;
  const [config] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("config")],
    program.programId
  );
  const users: TestUser[] = [];
  let playMint: anchor.web3.PublicKey;
  let nextFixture = 30_000_000;

  const outcomeValue = (name: OutcomeName) => ({ [name]: {} });
  const outcomeIndex = (name: OutcomeName) => ["home", "draw", "away"].indexOf(name);
  const user = (index: number): TestUser => {
    const value = users[index];
    if (!value) throw new Error(`Missing test user ${index}`);
    return value;
  };

  before(async () => {
    playMint = (await program.account.protocolConfig.fetch(config)).playMint;
    for (let index = 0; index < 3; index += 1) {
      const signer = anchor.web3.Keypair.generate();
      await provider.sendAndConfirm(
        new anchor.web3.Transaction().add(
          anchor.web3.SystemProgram.transfer({
            fromPubkey: payer.publicKey,
            toPubkey: signer.publicKey,
            lamports: 50_000_000
          })
        )
      );
      const tokenAccount = (
        await getOrCreateAssociatedTokenAccount(
          provider.connection,
          payer,
          playMint,
          signer.publicKey
        )
      ).address;
      const [faucetReceipt] = anchor.web3.PublicKey.findProgramAddressSync(
        [Buffer.from("faucet"), config.toBuffer(), signer.publicKey.toBuffer()],
        program.programId
      );
      await program.methods
        .claimDemoTokens()
        .accounts({
          user: signer.publicKey,
          config,
          playMint,
          userPlay: tokenAccount,
          faucetReceipt,
          tokenProgram: TOKEN_PROGRAM_ID,
          systemProgram: anchor.web3.SystemProgram.programId
        })
        .signers([signer])
        .rpc();
      users.push({ signer, tokenAccount });
    }
  });

  async function createMarket(): Promise<{
    fixtureId: number;
    market: anchor.web3.PublicKey;
    vault: anchor.web3.PublicKey;
  }> {
    const fixtureId = nextFixture++;
    const fixtureBytes = new anchor.BN(fixtureId).toArrayLike(Buffer, "le", 8);
    const [market] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("market"), fixtureBytes],
      program.programId
    );
    const vault = anchor.utils.token.associatedAddress({ mint: playMint, owner: market });
    await program.methods
      .createMarket(
        new anchor.BN(fixtureId),
        new anchor.BN(Math.floor(Date.now() / 1000) + 4)
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
    return { fixtureId, market, vault };
  }

  async function deposit(
    user: TestUser,
    market: anchor.web3.PublicKey,
    vault: anchor.web3.PublicKey,
    outcome: OutcomeName,
    amount: number
  ): Promise<void> {
    const [position] = anchor.web3.PublicKey.findProgramAddressSync(
      [
        Buffer.from("position"),
        market.toBuffer(),
        user.signer.publicKey.toBuffer(),
        Buffer.from([outcomeIndex(outcome)])
      ],
      program.programId
    );
    await program.methods
      .takePosition(outcomeValue(outcome), new anchor.BN(amount))
      .accounts({
        user: user.signer.publicKey,
        market,
        position,
        userPlay: user.tokenAccount,
        vault,
        tokenProgram: TOKEN_PROGRAM_ID,
        systemProgram: anchor.web3.SystemProgram.programId
      })
      .signers([user.signer])
      .rpc();
  }

  async function lock(market: anchor.web3.PublicKey): Promise<void> {
    for (let attempt = 0; attempt < 15; attempt += 1) {
      try {
        await program.methods.lockMarket().accounts({ market }).rpc();
        return;
      } catch (error) {
        if (attempt === 14 || !(error instanceof Error) || !error.message.includes("MarketStillOpen")) {
          throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
  }

  async function resolve(
    fixtureId: number,
    market: anchor.web3.PublicKey,
    home: number,
    away: number
  ): Promise<void> {
    await lock(market);
    await program.methods
      .resolveWithTxline({
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
          { stat: { key: 1, value: home, period: 100 }, statProof: [] },
          { stat: { key: 2, value: away, period: 100 }, statProof: [] }
        ]
      })
      .accounts({
        market,
        dailyScoresMerkleRoots: payer.publicKey,
        txoracleProgram: TXORACLE_PROGRAM
      })
      .rpc();
  }

  async function settle(
    instruction: "claimPayout" | "refundPosition",
    user: TestUser,
    market: anchor.web3.PublicKey,
    vault: anchor.web3.PublicKey,
    outcome: OutcomeName
  ): Promise<number> {
    const [position] = anchor.web3.PublicKey.findProgramAddressSync(
      [
        Buffer.from("position"),
        market.toBuffer(),
        user.signer.publicKey.toBuffer(),
        Buffer.from([outcomeIndex(outcome)])
      ],
      program.programId
    );
    const before = Number((await getAccount(provider.connection, user.tokenAccount)).amount);
    await program.methods[instruction](outcomeValue(outcome))
      .accounts({
        user: user.signer.publicKey,
        market,
        position,
        vault,
        userPlay: user.tokenAccount,
        tokenProgram: TOKEN_PROGRAM_ID
      })
      .signers([user.signer])
      .rpc();
    const after = Number((await getAccount(provider.connection, user.tokenAccount)).amount);
    return after - before;
  }

  it("pays winners proportionally and rejects duplicate claims", async () => {
    const { fixtureId, market, vault } = await createMarket();
    await deposit(user(0), market, vault, "home", 60);
    await deposit(user(1), market, vault, "home", 40);
    await deposit(user(2), market, vault, "away", 100);
    await resolve(fixtureId, market, 2, 0);

    expect(await settle("claimPayout", user(0), market, vault, "home")).to.equal(120);
    expect(await settle("claimPayout", user(1), market, vault, "home")).to.equal(80);
    await expectFailure(settle("claimPayout", user(0), market, vault, "home"));
  });

  it("assigns integer remainder to the final winning claim", async () => {
    const { fixtureId, market, vault } = await createMarket();
    await deposit(user(0), market, vault, "draw", 1);
    await deposit(user(1), market, vault, "draw", 2);
    await deposit(user(2), market, vault, "home", 7);
    await resolve(fixtureId, market, 1, 1);

    expect(await settle("claimPayout", user(0), market, vault, "draw")).to.equal(3);
    expect(await settle("claimPayout", user(1), market, vault, "draw")).to.equal(7);
    expect(Number((await getAccount(provider.connection, vault)).amount)).to.equal(0);
  });

  it("refunds deposits when nobody selected the winner", async () => {
    const { fixtureId, market, vault } = await createMarket();
    await deposit(user(0), market, vault, "home", 50);
    await resolve(fixtureId, market, 0, 1);
    expect(await settle("refundPosition", user(0), market, vault, "home")).to.equal(50);
  });
});
