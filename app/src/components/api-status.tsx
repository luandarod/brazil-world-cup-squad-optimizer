"use client";

import { useEffect, useState } from "react";

type ApiState =
  | { status: "loading" }
  | { status: "connected" }
  | { status: "missing" }
  | { status: "error"; message: string };

export function ApiStatus() {
  const [state, setState] = useState<ApiState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    fetch("/api/txline/status", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        if (!active) return;
        if (response.ok) setState({ status: "connected" });
        else if (response.status === 503) setState({ status: "missing" });
        else setState({ status: "error", message: body.error ?? "TxLINE indisponível" });
      })
      .catch(() => {
        if (active) setState({ status: "error", message: "Não foi possível consultar TxLINE" });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") return <span>TxLINE verificando</span>;
  if (state.status === "connected") return <span>TxLINE conectada</span>;
  if (state.status === "missing") return <span>TxLINE sem credenciais</span>;
  return <span>{state.message}</span>;
}
