export function ProofReceipt({
  fixtureId,
  score,
  slot,
  hash
}: {
  fixtureId: number;
  score: string;
  slot: number;
  hash: string;
}) {
  return (
    <article className="proof-receipt">
      <div className="receipt-head">
        <span>TxLINE validateStatV2</span>
        <b>DEMO LOCAL</b>
      </div>
      <div className="score-line">
        <small>FIXTURE {fixtureId}</small>
        <strong>{score}</strong>
      </div>
      <dl>
        <div><dt>Resultado</dt><dd>HOME</dd></div>
        <div><dt>Ambiente</dt><dd>validador local</dd></div>
        <div><dt>Slot de teste</dt><dd>{slot}</dd></div>
        <div><dt>Proof hash</dt><dd>{hash.slice(0, 8)}...{hash.slice(-8)}</dd></div>
      </dl>
    </article>
  );
}
