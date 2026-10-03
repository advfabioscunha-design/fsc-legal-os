"use client";

import { useCallback, useEffect, useState } from "react";
import PainelLayout from "../components/PainelLayout";
import { supabase } from "@/lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* FINANCEIRO — o que entra, o que sai, e o que ainda não aconteceu.
 *
 * A PERGUNTA QUE ESTA TELA RESPONDE
 *
 * "O escritório está ganhando dinheiro?" — que um dono faz todo mês e
 * que o sistema não sabia responder. Havia uma tabela de lançamentos
 * sem vencimento e sem baixa: um caixa de papel, que registra o que já
 * passou e não diz nada sobre o que vem.
 *
 * TRÊS SEPARAÇÕES QUE NÃO SÃO DETALHE
 *
 * 1. VENCIDO SEPARADO DE EM ABERTO. O que venceu e não foi pago é a
 *    única linha que exige ação hoje. Misturado no meio da lista, ele
 *    envelhece sem ninguém ver.
 *
 * 2. REALIZADO SEPARADO DE PREVISTO. Previsto é o que está lançado e
 *    ainda não aconteceu. Somar os dois num número só é como o
 *    escritório passa a achar que tem dinheiro que ainda não entrou.
 *
 * 3. O REPASSE DO PARCEIRO É CONTA A PAGAR. Nasce sozinho quando a
 *    prestação de contas é fechada, com o percentual da parceria sobre
 *    o honorário bruto. Antes dependia de alguém lembrar — e dívida que
 *    depende de memória não custa juros, custa o parceiro.
 *
 * OS TOTAIS VÊM DO SERVIDOR, não desta tela. Duas somas calculadas em
 * lugares diferentes divergem no dia em que alguém mudar um filtro de
 * um lado só, e aí ninguém sabe qual número está certo.
 */

type Conta = {
  id: string; tipo: string; categoria?: string; descricao?: string;
  valor: number; vencimento?: string; pago_em?: string; situacao: string;
  pessoa?: string; documento?: string; observacao?: string;
  parcela?: number; parcelas_total?: number; origem?: string;
  forma_pagamento?: string; caso_id?: string; parceiro_id?: string;
};

const reais = (v: any) =>
  (Number(v) || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const dataBr = (x?: string | null) =>
  x ? `${String(x).slice(8, 10)}/${String(x).slice(5, 7)}/${String(x).slice(0, 4)}` : "—";

const mesBr = (m: string) => {
  const nomes = ["jan", "fev", "mar", "abr", "mai", "jun",
                 "jul", "ago", "set", "out", "nov", "dez"];
  const [a, mm] = m.split("-");
  return `${nomes[Number(mm) - 1] ?? mm}/${a.slice(2)}`;
};

export default function Financeiro() {
  const [aba, setAba] = useState<"receber" | "pagar" | "fluxo">("receber");
  const [dados, setDados] = useState<{ contas: Conta[]; totais: any }>({ contas: [], totais: {} });
  const [fluxo, setFluxo] = useState<any[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState("");
  const [nova, setNova] = useState(false);
  const [form, setForm] = useState({
    tipo: "ENTRADA", descricao: "", valor: "", vencimento: "",
    pessoa: "", categoria: "", documento: "", parcelas: "1", observacao: "",
  });

  const chamar = useCallback(async (caminho: string, opcoes: any = {}) => {
    const { data } = await supabase.auth.getSession();
    const r = await fetch(`${API}${caminho}`, {
      ...opcoes,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${data.session?.access_token}`,
        ...(opcoes.headers || {}),
      },
    });
    const d = await r.json().catch(() => ({} as any));
    return { ok: r.ok, status: r.status, dados: d };
  }, []);

  const carregar = useCallback(async () => {
    setCarregando(true);
    if (aba === "fluxo") {
      const r = await chamar("/api/v1/financeiro/fluxo-caixa?meses=6");
      if (!r.ok) { setErro(r.dados?.detail || "Não consegui carregar o fluxo de caixa."); setFluxo([]); }
      else { setErro(""); setFluxo(Array.isArray(r.dados) ? r.dados : []); }
    } else {
      const tipo = aba === "receber" ? "ENTRADA" : "SAIDA";
      const r = await chamar(`/api/v1/financeiro/contas?tipo=${tipo}`);
      if (!r.ok) {
        setErro(r.status === 401 || r.status === 403
          ? "Esta tela é da equipe do escritório."
          : (r.dados?.detail || "Não consegui carregar as contas."));
        setDados({ contas: [], totais: {} });
      } else {
        setErro("");
        setDados({ contas: r.dados?.contas || [], totais: r.dados?.totais || {} });
      }
    }
    setCarregando(false);
  }, [aba, chamar]);

  useEffect(() => { carregar(); }, [carregar]);

  async function lancar() {
    if (!form.descricao.trim()) { alert("Descreva a conta."); return; }
    const valor = Number(String(form.valor).replace(/\./g, "").replace(",", "."));
    if (!(valor > 0)) { alert("Informe um valor maior que zero."); return; }
    if (!form.vencimento) { alert("Informe o vencimento."); return; }
    setOcupado("nova");
    const r = await chamar("/api/v1/financeiro/contas", {
      method: "POST",
      body: JSON.stringify({ ...form, valor, parcelas: Number(form.parcelas) || 1 }),
    });
    setOcupado("");
    if (!r.ok) { alert(r.dados?.detail || "Não consegui lançar a conta."); return; }
    setForm({ tipo: aba === "pagar" ? "SAIDA" : "ENTRADA", descricao: "", valor: "",
              vencimento: "", pessoa: "", categoria: "", documento: "",
              parcelas: "1", observacao: "" });
    setNova(false); carregar();
  }

  async function baixar(c: Conta) {
    const forma = window.prompt(
      `${c.tipo === "ENTRADA" ? "Recebido" : "Pago"} — ${reais(c.valor)}\n\n`
      + "Como? (PIX, transferência, dinheiro, boleto…)");
    if (forma === null) return;
    setOcupado(c.id);
    const r = await chamar(`/api/v1/financeiro/contas/${c.id}/baixar`, {
      method: "POST", body: JSON.stringify({ forma_pagamento: forma }),
    });
    setOcupado("");
    if (!r.ok) { alert(r.dados?.detail || "Não consegui dar baixa."); return; }
    carregar();
  }

  async function estornar(c: Conta) {
    if (!window.confirm(
      `Estornar a baixa de ${reais(c.valor)}?\n\n`
      + "A conta volta para em aberto. O estorno fica registrado.")) return;
    setOcupado(c.id);
    const r = await chamar(`/api/v1/financeiro/contas/${c.id}/estornar`, { method: "POST" });
    setOcupado("");
    if (!r.ok) { alert(r.dados?.detail || "Não consegui estornar."); return; }
    carregar();
  }

  const t = dados.totais || {};
  const vencidas = dados.contas.filter((c) => c.situacao === "VENCIDO");
  const abertas = dados.contas.filter((c) => c.situacao === "ABERTO");
  const pagas = dados.contas.filter((c) => c.situacao === "PAGO");

  const Cartao = ({ c }: { c: Conta }) => {
    const cor = c.situacao === "VENCIDO" ? "#C0392B"
      : c.situacao === "PAGO" ? "#1DB954" : "#C9A84C";
    return (
      <li className="rounded-xl border px-4 py-3"
        style={{ borderColor: `${cor}44`, background: `${cor}0F` }}>
        <div className="flex flex-wrap items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-white">{c.descricao}</p>
            <p className="mt-0.5 text-[12px] text-white/45">
              {[c.pessoa,
                c.vencimento && `vence ${dataBr(c.vencimento)}`,
                c.pago_em && `${c.tipo === "ENTRADA" ? "recebido" : "pago"} em ${dataBr(c.pago_em)}`,
                c.forma_pagamento,
                c.categoria,
                c.documento].filter(Boolean).join(" · ")}
            </p>
            {c.origem === "REPASSE" && (
              <p className="mt-1 text-[11px] text-[#2D7DD2]">
                Repasse de parceria — nasceu da prestação de contas do caso.
              </p>
            )}
            {c.origem === "PRESTACAO" && (
              <p className="mt-1 text-[11px] text-[#2D7DD2]">
                Honorários lançados pela prestação de contas.
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="font-mono text-base font-bold" style={{ color: cor }}>
              {reais(c.valor)}
            </p>
            <p className="text-[10px] font-bold" style={{ color: cor }}>{c.situacao}</p>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {c.situacao === "PAGO" ? (
            <button disabled={ocupado === c.id} onClick={() => estornar(c)}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/60 hover:border-white/40">
              Estornar baixa
            </button>
          ) : (
            <button disabled={ocupado === c.id} onClick={() => baixar(c)}
              className="rounded-lg bg-[#1DB954] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#17a349] disabled:opacity-40">
              {ocupado === c.id ? "…" : c.tipo === "ENTRADA" ? "Recebi" : "Paguei"}
            </button>
          )}
        </div>
      </li>
    );
  };

  const Grupo = ({ titulo, nota, itens }: { titulo: string; nota?: string; itens: Conta[] }) =>
    itens.length === 0 ? null : (
      <section>
        <h2 className="mb-1 font-display text-base font-bold text-white">
          {titulo} ({itens.length})
        </h2>
        {nota && <p className="mb-2 text-[12px] text-white/45">{nota}</p>}
        <ul className="space-y-2">{itens.map((c) => <Cartao key={c.id} c={c} />)}</ul>
      </section>
    );

  return (
    <PainelLayout titulo="Financeiro">
      <div className="mb-4 flex flex-wrap gap-2">
        {([["receber", "A receber"], ["pagar", "A pagar"], ["fluxo", "Fluxo de caixa"]] as const)
          .map(([k, r]) => (
          <button key={k} onClick={() => { setAba(k); setNova(false); }}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
              aba === k ? "bg-[#C9A84C] text-[#0A1628]"
                        : "border border-white/15 text-white/60 hover:border-white/40"}`}>
            {r}
          </button>
        ))}
        {aba !== "fluxo" && (
          <button onClick={() => {
            setForm({ ...form, tipo: aba === "pagar" ? "SAIDA" : "ENTRADA" });
            setNova(!nova);
          }}
            className="ml-auto rounded-lg border border-white/15 px-4 py-1.5 text-sm font-semibold text-white/80 hover:border-white/40">
            {nova ? "Cancelar" : aba === "pagar" ? "+ Nova conta a pagar" : "+ Nova conta a receber"}
          </button>
        )}
      </div>

      {erro && (
        <p className="mb-4 rounded-xl border border-[#C0392B]/40 bg-[#C0392B]/10 px-4 py-3 text-sm text-white">
          {erro}
        </p>
      )}

      {nova && aba !== "fluxo" && (
        <div className="mb-5 space-y-3 rounded-xl border border-[#C9A84C]/30 bg-[#0B1F3B] p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="text-xs text-white/60">Descrição
              <input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                placeholder={aba === "pagar" ? "Aluguel, contador, assinatura…" : "Honorários, entrada do contrato…"}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
            </label>
            <label className="text-xs text-white/60">
              {aba === "pagar" ? "A quem se paga" : "Quem paga"}
              <input value={form.pessoa} onChange={(e) => setForm({ ...form, pessoa: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
            </label>
            <label className="text-xs text-white/60">Valor total (R$)
              <input value={form.valor} inputMode="decimal" placeholder="0,00"
                onChange={(e) => setForm({ ...form, valor: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
            </label>
            <label className="text-xs text-white/60">Primeiro vencimento
              <input type="date" value={form.vencimento}
                onChange={(e) => setForm({ ...form, vencimento: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
            </label>
            <label className="text-xs text-white/60">Parcelas
              <input value={form.parcelas} inputMode="numeric"
                onChange={(e) => setForm({ ...form, parcelas: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
            </label>
            <label className="text-xs text-white/60">Categoria (opcional)
              <input value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
            </label>
          </div>
          <p className="text-[11px] text-white/40">
            Parcelado, cada parcela vira uma conta com o seu próprio vencimento — e a
            diferença de centavos vai na primeira, para três parcelas de R$ 100,00 não
            somarem R$ 99,99.
          </p>
          <button onClick={lancar} disabled={ocupado === "nova"}
            className="rounded-lg bg-[#C9A84C] px-4 py-2 text-sm font-bold text-[#0A1628] hover:brightness-110 disabled:opacity-40">
            {ocupado === "nova" ? "Lançando…" : "Lançar"}
          </button>
        </div>
      )}

      {carregando ? (
        <p className="text-sm text-[#8899AA]">Carregando…</p>
      ) : aba === "fluxo" ? (
        <section className="space-y-2">
          <p className="mb-3 text-[12px] leading-relaxed text-white/45">
            Seis meses. <b className="text-white/70">Realizado</b> é o que já entrou e
            saiu de verdade; <b className="text-white/70">previsto</b> é o que está
            lançado e ainda não aconteceu. Os dois ficam separados de propósito — somados,
            viram a conta que faz o escritório gastar dinheiro que ainda não recebeu.
          </p>
          {fluxo.length === 0 ? (
            <p className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5 text-center text-sm text-white/45">
              Ainda não há lançamentos no período.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-white/10">
              <table className="w-full text-sm">
                <thead className="bg-[#0B1F3B] text-[11px] uppercase tracking-wide text-white/45">
                  <tr>
                    <th className="px-3 py-2 text-left">Mês</th>
                    <th className="px-3 py-2 text-right">Entrou</th>
                    <th className="px-3 py-2 text-right">Saiu</th>
                    <th className="px-3 py-2 text-right">Saldo</th>
                    <th className="px-3 py-2 text-right">Previsto a entrar</th>
                    <th className="px-3 py-2 text-right">Previsto a sair</th>
                    <th className="px-3 py-2 text-right">Saldo com o previsto</th>
                  </tr>
                </thead>
                <tbody>
                  {fluxo.map((m) => (
                    <tr key={m.mes} className="border-t border-white/5">
                      <td className="px-3 py-2 font-semibold text-white">{mesBr(m.mes)}</td>
                      <td className="px-3 py-2 text-right font-mono text-[#1DB954]">{reais(m.entradas)}</td>
                      <td className="px-3 py-2 text-right font-mono text-[#E57373]">{reais(m.saidas)}</td>
                      <td className="px-3 py-2 text-right font-mono font-bold"
                        style={{ color: m.saldo >= 0 ? "#1DB954" : "#C0392B" }}>{reais(m.saldo)}</td>
                      <td className="px-3 py-2 text-right font-mono text-white/45">{reais(m.previsto_entradas)}</td>
                      <td className="px-3 py-2 text-right font-mono text-white/45">{reais(m.previsto_saidas)}</td>
                      <td className="px-3 py-2 text-right font-mono"
                        style={{ color: m.saldo_previsto >= 0 ? "#C9A84C" : "#C0392B" }}>
                        {reais(m.saldo_previsto)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {(aba === "receber"
              ? [["Vencido e não recebido", t.vencido_receber, "#C0392B"],
                 ["A receber", t.a_receber, "#C9A84C"],
                 ["Já recebido", t.recebido, "#1DB954"]]
              : [["Vencido e não pago", t.vencido_pagar, "#C0392B"],
                 ["A pagar", t.a_pagar, "#C9A84C"],
                 ["Já pago", t.pago, "#1DB954"]]
            ).map(([rotulo, valor, cor]: any) => (
              <div key={rotulo} className="rounded-xl border border-white/10 bg-[#0B1F3B] px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-white/40">{rotulo}</p>
                <p className="mt-1 font-mono text-lg font-bold" style={{ color: cor }}>
                  {reais(valor)}
                </p>
              </div>
            ))}
          </div>

          <Grupo titulo="Venceu e não foi quitado" itens={vencidas}
            nota="É a única parte desta tela que pede ação hoje. Fica em cima por isso." />
          <Grupo titulo="Em aberto" itens={abertas} />
          <Grupo titulo="Quitado" itens={pagas} />

          {dados.contas.length === 0 && (
            <p className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5 text-center text-sm text-white/45">
              Nenhuma conta {aba === "receber" ? "a receber" : "a pagar"} lançada.
            </p>
          )}
        </div>
      )}
    </PainelLayout>
  );
}
