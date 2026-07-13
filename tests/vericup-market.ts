import * as anchor from "@coral-xyz/anchor";
import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  TOKEN_PROGRAM_ID,
  createMint,
  getAccount,
  getOrCreateAssociatedTokenAccount
} from "./token-helpers";
import { expect } from "chai";

async function expectFailure(promise: Promise<unknown>): Promise<void> {
  try {
    await promise;
    expect.fail("Expected transaction to fail");
  } catch (error) {
    expect(error).to.be.instanceOf(Error);
  }
}

describe("vericup market", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  // The generated client does not expose instructions until the RED phase builds
  // the program IDL, so keep this contract test deliberately IDL-agnostic.
  const program = anchor.workspace.Vericup as any;
  const payer = (provider.wallet as anchor.Wallet).payer;
  const [config] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("config")],
    program.programId
  );

  let playMint: anchor.web3.PublicKey;
  let userPlay: anchor.web3.PublicKey;

  before(async () => {
    playMint = await createMint(provider.connection, payer, config, null, 6);
    userPlay = (await getOrCreateAssociatedTokenAccount(
      provider.connection,
      payer,
      playMint,
      payer.publicKey
    )).address;
  });

  it("initialises one protocol with the configured PLAY mint", async () => {
    await program.methods.initializeProtocol().accounts({
      authority: payer.publicKey,
      config,
      playMint,
      systemProgram: anchor.web3.SystemProgram.programId
    }).rpc();

    const account = await program.account.protocolConfig.fetch(config);
    expect(account.authority.equals(payer.publicKey)).to.equal(true);
    expect(account.playMint.equals(playMint)).to.equal(true);
  });

  it("mints 1,000 PLAY only once per wallet", async () => {
    const [faucetReceipt] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("faucet"), config.toBuffer(), payer.publicKey.toBuffer()],
      program.programId
    );
    const accounts = {
      user: payer.publicKey,
      config,
      playMint,
      userPlay,
      faucetReceipt,
      tokenProgram: TOKEN_PROGRAM_ID,
      systemProgram: anchor.web3.SystemProgram.programId
    };

    await program.methods.claimDemoTokens().accounts(accounts).rpc();

    expect(Number((await getAccount(provider.connection, userPlay)).amount)).to.equal(1_000_000_000);
    await expectFailure(program.methods.claimDemoTokens().accounts(accounts).rpc());
  });

  it("creates one fixture market and accepts all outcomes before kickoff", async () => {
    const fixtureId = new anchor.BN(18175981);
    const kickoff = new anchor.BN(Math.floor(Date.now() / 1000) + 60);
    const [market] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("market"), fixtureId.toArrayLike(Buffer, "le", 8)],
      program.programId
    );
    const vault = anchor.utils.token.associatedAddress({ mint: playMint, owner: market });

    await program.methods.createMarket(fixtureId, kickoff).accounts({
      authority: payer.publicKey,
      config,
      playMint,
      market,
      vault,
      tokenProgram: TOKEN_PROGRAM_ID,
      associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
      systemProgram: anchor.web3.SystemProgram.programId
    }).rpc();

    for (const [outcome, amount] of [[{ home: {} }, 100], [{ draw: {} }, 50], [{ away: {} }, 25]] as const) {
      const outcomeIndex = "home" in outcome ? 0 : "draw" in outcome ? 1 : 2;
      const [position] = anchor.web3.PublicKey.findProgramAddressSync(
        [Buffer.from("position"), market.toBuffer(), payer.publicKey.toBuffer(), Buffer.from([outcomeIndex])],
        program.programId
      );
      await program.methods.takePosition(outcome, new anchor.BN(amount)).accounts({
        user: payer.publicKey,
        market,
        position,
        userPlay,
        vault,
        tokenProgram: TOKEN_PROGRAM_ID,
        systemProgram: anchor.web3.SystemProgram.programId
      }).rpc();
    }

    const account = await program.account.market.fetch(market);
    expect(account.fixtureId.toNumber()).to.equal(18175981);
    expect(account.pools.map((value: anchor.BN) => value.toNumber())).to.deep.equal([100, 50, 25]);
  });
});
