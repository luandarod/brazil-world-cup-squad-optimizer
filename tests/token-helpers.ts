import * as anchor from "@coral-xyz/anchor";

export const TOKEN_PROGRAM_ID = anchor.utils.token.TOKEN_PROGRAM_ID;
export const ASSOCIATED_TOKEN_PROGRAM_ID = anchor.utils.token.ASSOCIATED_PROGRAM_ID;

const MINT_SIZE = 82;
const ACCOUNT_SIZE = 165;

function cOptionPubkey(value: anchor.web3.PublicKey | null): Buffer {
  const buffer = Buffer.alloc(36);
  if (value) {
    buffer.writeUInt32LE(1, 0);
    value.toBuffer().copy(buffer, 4);
  }
  return buffer;
}

function initializeMintData(
  decimals: number,
  mintAuthority: anchor.web3.PublicKey,
  freezeAuthority: anchor.web3.PublicKey | null
): Buffer {
  return Buffer.concat([
    Buffer.from([0, decimals]),
    mintAuthority.toBuffer(),
    cOptionPubkey(freezeAuthority)
  ]);
}

function createAssociatedTokenAccountInstruction(
  payer: anchor.web3.PublicKey,
  associatedToken: anchor.web3.PublicKey,
  owner: anchor.web3.PublicKey,
  mint: anchor.web3.PublicKey
): anchor.web3.TransactionInstruction {
  return new anchor.web3.TransactionInstruction({
    programId: ASSOCIATED_TOKEN_PROGRAM_ID,
    keys: [
      { pubkey: payer, isSigner: true, isWritable: true },
      { pubkey: associatedToken, isSigner: false, isWritable: true },
      { pubkey: owner, isSigner: false, isWritable: false },
      { pubkey: mint, isSigner: false, isWritable: false },
      { pubkey: anchor.web3.SystemProgram.programId, isSigner: false, isWritable: false },
      { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false }
    ],
    data: Buffer.alloc(0)
  });
}

export async function createMint(
  connection: anchor.web3.Connection,
  payer: anchor.web3.Keypair,
  mintAuthority: anchor.web3.PublicKey,
  freezeAuthority: anchor.web3.PublicKey | null,
  decimals: number
): Promise<anchor.web3.PublicKey> {
  const mint = anchor.web3.Keypair.generate();
  const lamports = await connection.getMinimumBalanceForRentExemption(MINT_SIZE);
  const transaction = new anchor.web3.Transaction().add(
    anchor.web3.SystemProgram.createAccount({
      fromPubkey: payer.publicKey,
      newAccountPubkey: mint.publicKey,
      lamports,
      space: MINT_SIZE,
      programId: TOKEN_PROGRAM_ID
    }),
    new anchor.web3.TransactionInstruction({
      programId: TOKEN_PROGRAM_ID,
      keys: [
        { pubkey: mint.publicKey, isSigner: false, isWritable: true },
        { pubkey: anchor.web3.SYSVAR_RENT_PUBKEY, isSigner: false, isWritable: false }
      ],
      data: initializeMintData(decimals, mintAuthority, freezeAuthority)
    })
  );
  await anchor.web3.sendAndConfirmTransaction(connection, transaction, [payer, mint]);
  return mint.publicKey;
}

export async function getOrCreateAssociatedTokenAccount(
  connection: anchor.web3.Connection,
  payer: anchor.web3.Keypair,
  mint: anchor.web3.PublicKey,
  owner: anchor.web3.PublicKey
): Promise<{ address: anchor.web3.PublicKey }> {
  const address = anchor.utils.token.associatedAddress({ mint, owner });
  if (await connection.getAccountInfo(address)) return { address };
  await anchor.web3.sendAndConfirmTransaction(
    connection,
    new anchor.web3.Transaction().add(
      createAssociatedTokenAccountInstruction(payer.publicKey, address, owner, mint)
    ),
    [payer]
  );
  return { address };
}

export async function getAccount(
  connection: anchor.web3.Connection,
  address: anchor.web3.PublicKey
): Promise<{ amount: bigint }> {
  const account = await connection.getAccountInfo(address);
  if (!account) throw new Error(`Missing token account ${address.toBase58()}`);
  if (account.data.length < ACCOUNT_SIZE) throw new Error(`Invalid token account ${address.toBase58()}`);
  return { amount: account.data.readBigUInt64LE(64) };
}
