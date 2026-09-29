"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import VisualizadorProtegido from "../../components/VisualizadorProtegido";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* O PEDIDO, DO LADO DO CLIENTE

   Esta tela não é a área de acompanhamento de processo — é outra
   coisa, e de propósito: aqui o cliente responde perguntas, manda
   documento, vê em que fase está e, no fim, lê a minuta e aprova ou
   pede mudança. Uma coluna só, poucas decisões por vez. */

const FASES: { id: string; rotulo: string }[] = [
  { id: "COLETA", rotulo: "Coleta de informações" },
  { id: "CIENCIA", rotulo: "Orientação e ciência" },
  { id: "PAGAMENTO", rotulo: "Pagamento" },
  { id: "REDACAO", rotulo: "Elaboração" },
  { id: "REVISAO_IA", rotulo: "Revisão técnica" },
  { id: "AJUSTE", rotulo: "Ajustes" },
  { id: "REVISAO_ADV", rotulo: "Revisão do advogado" },
  { id: "APROVACAO", rotulo: "Sua aprovação" },
  { id: "ASSINATURA", rotulo: "Assinatura" },
  { id: "ENTREGUE", rotulo: "Entregue" },
];

export default function PedidoDoCliente() {
  const { id } = useParams<{ id: string }>();
  const [pedido, setPedido] = useState<any>(null);
  const [tipo, setTipo] = useState<any>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [observacoes, setObservacoes] = useState("");
  const [alteracao, setAlteracao] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");

  async function carregar() {
    const p = await fetch(`${API}/api/v1/contratos/pedidos/${id}`).then((r) => r.json());
    setPedido(p);
    setValores(p?.dados || {});
    setObservacoes(p?.observacoes || "");
    if (p?.tipo) {
      const t = await fetch(`${API}/api/v1/contratos/tipos/${p.tipo}`).then((r) => r.json());
      setTipo(t);
    }
  }
  useEffect(() => { carregar(); /* eslint-disable-next-line */ }, [id]);

  const faseAtual = pedido?.fase || "COLETA";
  const indiceFase = Math.max(0, FASES.findIndex((f) => f.id === faseAtual));
  const nomeCliente = pedido?.clientes?.nome || "cliente";

  async function salvarColeta() {
    setOcupado(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/dados`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dados: valores, observacoes }),
      });
      if (r.ok) { setAviso("Informações salvas. Pode continuar depois, se preferir."); carregar(); }
      else setAviso("Não foi possível salvar agora.");
    } finally { setOcupado(false); }
  }

  async function aprovar() {
    if (!confirm("Aprovar este documento e seguir para assinatura?")) return;
    setOcupado(true);
    try {
      await fetch(`${API}/api/v1/contratos/pedidos/${id}/aprovar`, { method: "POST" });
      carregar();
    } finally { setOcupado(false); }
  }

  async function pedirAlteracao() {
    if (alteracao.trim().length < 10) {
      setAviso("Escreva o que precisa ser alterado, com o máximo de detalhe possível.");
      return;
    }
    setOcupado(true);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/alteracao`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: alteracao }),
      });
      if (r.ok) { setAlteracao(""); setAviso("Pedido de alteração enviado."); carregar(); }
    } finally { setOcupado(false); }
  }

  if (!pedido) {
    return <main className="flex min-h-screen items-center justify-center bg-[#0A1628] text-white/60">Carregando…</main>;
  }

  const obrigatoriosFaltando = (tipo?.campos || [])
    .filter((c: any) => c.obrigatorio && !(valores[c.campo] || "").trim()).length;

  return (
    <main className="min-h-screen bg-[#0A1628] px-4 py-8 text-white">
      <div className="mx-auto max-w-2xl space-y-5">
        <header>
          <p className="text-xs text-white/40">{pedido.numero}</p>
          <h1 className="text-xl font-bold">{tipo?.nome || pedido.tipo}</h1>
          <p className="mt-0.5 text-xs text-white/50">{tipo?.base_legal}</p>
        </header>

        {/* Em que fase está */}
        <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-4">
          <p className="mb-3 text-xs font-bold text-[#C9A24D]">Andamento do pedido</p>
          <div className="space-y-1.5">
            {FASES.map((f, i) => (
              <div key={f.id} className="flex items-center gap-2.5">
                <span className={`h-2 w-2 shrink-0 rounded-full ${
                  i < indiceFase ? "bg-[#1DB954]" : i === indiceFase ? "bg-[#C9A84C]" : "bg-white/15"}`} />
                <span className={`text-xs ${
                  i === indiceFase ? "font-bold text-white" : i < indiceFase ? "text-white/55" : "text-white/30"}`}>
                  {f.rotulo}
                </span>
              </div>
            ))}
          </div>
        </section>

        {aviso && (
          <p className="rounded-lg border border-[#2D7DD2]/40 bg-[#2D7DD2]/10 px-3 py-2 text-xs text-white/80">{aviso}</p>
        )}

        {/* COLETA */}
        {faseAtual === "COLETA" && tipo && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <h2 className="text-sm font-bold text-[#C9A24D]">Informações necessárias</h2>
            <p className="mt-1 text-xs text-white/50">
              Preencha o que souber. Pode também enviar cópia dos documentos e
              o atendente extrai os dados por você.
            </p>

            <div className="mt-4 space-y-3">
              {(tipo.campos || []).map((c: any) => (
                <label key={c.campo} className="block">
                  <span className="text-xs text-white/70">
                    {c.rotulo}{c.obrigatorio && <span className="text-[#C0392B]"> *</span>}
                  </span>
                  {c.porque && (
                    <span className="block text-[10px] text-white/35">por que pedimos: {c.porque}</span>
                  )}
                  <input
                    value={valores[c.campo] || ""}
                    onChange={(e) => setValores({ ...valores, [c.campo]: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
                </label>
              ))}

              <label className="block">
                <span className="text-xs text-white/70">
                  Como as partes combinaram? Escreva com suas palavras
                </span>
                <span className="block text-[10px] text-white/35">
                  é aqui que aparecem os detalhes que mudam o contrato
                </span>
                <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)}
                  rows={4}
                  className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button onClick={salvarColeta} disabled={ocupado}
                className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
                {ocupado ? "Salvando…" : "Salvar informações"}
              </button>
              <span className="text-xs text-white/45">
                {obrigatoriosFaltando > 0
                  ? `${obrigatoriosFaltando} campo(s) obrigatório(s) em aberto`
                  : "todos os campos obrigatórios preenchidos"}
              </span>
            </div>
          </section>
        )}

        {/* APROVAÇÃO — minuta com marca d'água */}
        {faseAtual === "APROVACAO" && pedido.minuta && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <h2 className="mb-3 text-sm font-bold text-[#C9A24D]">
              Seu documento, para conferência
            </h2>
            <VisualizadorProtegido texto={pedido.minuta} quemVe={nomeCliente}
              titulo={tipo?.nome} />

            <div className="mt-5 space-y-3">
              <button onClick={aprovar} disabled={ocupado}
                className="w-full rounded-lg bg-[#1DB954] py-3 text-sm font-bold text-white hover:bg-[#17a349] disabled:opacity-50">
                Aprovar e seguir para assinatura
              </button>

              <div className="rounded-xl border border-white/10 p-3">
                <p className="text-xs font-semibold text-white/70">
                  Precisa de alguma alteração? Escreva exatamente o que mudar:
                </p>
                <textarea value={alteracao} onChange={(e) => setAlteracao(e.target.value)}
                  rows={3} placeholder="Ex.: o prazo é de 30 meses, não 24; incluir que o condomínio é por conta do locatário…"
                  className="mt-2 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
                <button onClick={pedirAlteracao} disabled={ocupado}
                  className="mt-2 rounded-lg border border-[#E5A44C]/60 px-4 py-2 text-sm font-semibold text-[#E5A44C] hover:bg-[#E5A44C]/10 disabled:opacity-50">
                  Pedir alteração
                </button>
              </div>
            </div>
          </section>
        )}

        {/* Fases em que a bola está com o escritório */}
        {["PAGAMENTO", "REDACAO", "REVISAO_IA", "AJUSTE", "REVISAO_ADV",
          "ASSINATURA", "ENTREGUE"].includes(faseAtual) && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5 text-sm text-white/70">
            {faseAtual === "PAGAMENTO" && (
              <>
                <p className="font-bold text-white/90">Pagamento por PIX</p>
                <p className="mt-1 text-xs">
                  Valor: <b className="text-[#C9A24D]">
                    {Number(pedido.valor || 0).toLocaleString("pt-BR",
                      { style: "currency", currency: "BRL" })}
                  </b>. O escritório envia a chave PIX pelo chat e por e-mail.
                  O trabalho começa assim que o pagamento é confirmado.
                </p>
              </>
            )}
            {faseAtual === "REDACAO" && <p>Seu documento está sendo elaborado.</p>}
            {faseAtual === "REVISAO_IA" && <p>O documento está em revisão técnica.</p>}
            {faseAtual === "AJUSTE" && <p>Aplicando os ajustes apontados na revisão.</p>}
            {faseAtual === "REVISAO_ADV" && (
              <p>Na mesa do advogado para revisão final. Nada é enviado a você
                 antes dessa conferência.</p>
            )}
            {faseAtual === "ASSINATURA" && (
              <p>Enviado para assinatura eletrônica. Quando todos assinarem, a
                 cópia final vai para o seu e-mail.</p>
            )}
            {faseAtual === "ENTREGUE" && (
              <p className="text-[#1DB954]">Documento entregue. A cópia assinada
                 está no seu e-mail.</p>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
