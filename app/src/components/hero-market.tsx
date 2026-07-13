"use client";

import { useState } from "react";
import { MarketCard } from "./market-card";

export function HeroMarket() {
  const [focusKey, setFocusKey] = useState(0);
  const focusMarket = () => setFocusKey((value) => value + 1);

  return (
    <>
      <nav className="nav shell" aria-label="Principal">
        <a className="brand" href="#top">VERICUP</a>
        <div><a href="#copa">Copa</a><a href="#prova">Prova</a><a href="#arquitetura">Arquitetura</a></div>
        <button className="nav-cta" onClick={focusMarket} type="button">Testar</button>
      </nav>

      <section className="hero shell" id="top">
        <div className="hero-copy">
          <p className="eyebrow">MERCADOS DA COPA SEM CARTEIRA</p>
          <h1>Você prevê. A prova liquida.</h1>
          <p className="lede">Palpites convidados com PLAY virtual, placares TxLINE e uma camada Solana opcional para provar o resultado quando isso importa.</p>
          <button className="hero-cta" onClick={focusMarket} type="button">Testar mercado</button>
        </div>
        <div id="mercado" className="hero-product">
          <MarketCard focusKey={focusKey} home="França" away="Espanha" kickoff="14 JUL, 19:00 UTC" pools={[612, 488, 351]} />
        </div>
      </section>
    </>
  );
}
