import { ApiStatus } from "../components/api-status";
import { CupFixtureGrid } from "../components/cup-fixture-grid";
import { HeroMarket } from "../components/hero-market";
import { ProofReceipt } from "../components/proof-receipt";

export default function Home() {
  return (
    <main>
      <HeroMarket />

      <section className="signal-strip" aria-label="Garantias">
        <div className="shell">
          <span>Sem carteira</span><ApiStatus /><span>Copa inteira</span><span>PLAY sem valor real</span>
        </div>
      </section>

      <CupFixtureGrid />

      <section className="proof-section shell" id="prova">
        <div className="section-copy">
          <h2>O placar não entra pela confiança.</h2>
          <p>O keeper observa TxLINE, deriva o resultado e pode enviar a prova Merkle para o programa Anchor. A carteira fica no lado operacional, não no caminho do torcedor.</p>
        </div>
        <ProofReceipt fixtureId={18175981} score="2 - 1" slot={421337991} hash="a19c72f6e8b42291147f9a9bdac33f08" />
      </section>

      <section className="architecture shell" id="arquitetura">
        <h2>Um caminho curto para acertar e provar.</h2>
        <div className="flow" aria-label="Fluxo de resolução">
          <article><b>Torcedor</b><p>Registra palpite convidado com PLAY virtual.</p></article>
          <span aria-hidden="true">-&gt;</span>
          <article><b>TxLINE + Keeper</b><p>Recebe SSE, snapshots e proofs para travar mercados e calcular o resultado.</p></article>
          <span aria-hidden="true">-&gt;</span>
          <article><b>Prova opcional</b><p>Valida CPI na Solana e gera recibo verificável.</p></article>
        </div>
      </section>

      <footer className="footer shell">
        <div><strong>VERICUP MARKETS</strong><p>Settlement esportivo verificável.</p></div>
        <p>Construído para o TxODDS Prediction Markets and Settlement bounty.</p>
      </footer>
    </main>
  );
}
