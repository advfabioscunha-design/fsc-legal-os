"use client";
import { useCallback, useEffect, useState } from "react";
import PainelLayout from "../components/PainelLayout";
import { comoLista, comoTexto } from "@/lib/listas";
import AvisoDaIA from "@/app/components/AvisoDaIA";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* O BANCO DE CLIENTES DO ESCRITÓRIO.
 *
 * A base sempre existiu; o que não existia era uma porta para olhar a
 * base INTEIRA. Quem quisesse saber quantos clientes o escritório tem,
 * ou quem faz aniversário este mês, teria de abrir caso por caso.
 *
 * O filtro mais útil desta tela é o menos óbvio: "sem data de
 * nascimento". É a lista do trabalho que falta para a felicitação
 * funcionar. Sem ele, descobre-se que metade da base não tem a data no
 * dia em que alguém reclama de não ter recebido parabéns.
 */

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

export default function Clientes() {
  const [lista, setLista] = useState<any[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [mes, setMes] = useState(0);
  const [semNascimento, setSemNascimento] = useState(false);
  const [descadastrados, setDescadastrados] = useState(false);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  const [hoje, setHoje] = useState<any[]>([]);
  const [novo, setNovo] = useState<any>(null);

  const carregar = useCallback(async () => {
    setCarregando(true); setErro("");
    try {
      const q = new URLSearchParams({
        busca, pagina: String(pagina),
        mes_aniversario: String(mes),
        sem_nascimento: String(semNascimento),
        descadastrados: String(descadastrados),
      });
      const r = await fetch(`${API}/api/v1/clientes?${q}`);
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        // O DETALHE TÉCNICO VAI PARA A TELA
        //
        // "Deu erro no servidor" não diz a quem está olhando se o
        // problema é uma migração que falta, uma permissão ou a rede.
        // O servidor manda o detalhe para quem é da equipe; esconder
        // isso só obriga a abrir o log para descobrir o óbvio.
        setErro([j?.detail || "Não consegui carregar a base.", j?.tecnico]
          .filter(Boolean).join("  —  "));
      } else {
        setLista(comoLista(j?.clientes));
        setTotal(j?.total ?? null);
        setAviso(comoTexto(j?.aviso));
      }
    } catch { setErro("Falha de conexão."); }
    setCarregando(false);
  }, [busca, pagina, mes, semNascimento, descadastrados]);

  useEffect(() => { carregar(); }, [carregar]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/relacionamento/aniversariantes`);
        const j = await r.json().catch(() => ({}));
        setHoje(comoLista(j?.aniversariantes));
      } catch { /* sem aniversariantes é um estado válido */ }
    })();
  }, []);

  async function mudar(id: string, campos: any) {
    try {
      await fetch(`${API}/api/v1/clientes/${id}/relacionamento`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(campos),
      });
      carregar();
    } catch { /* a lista recarrega na próxima ação */ }
  }

  const cx = "rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A24D]";
  const semData = lista.filter((c) => !c.data_nascimento).length;

  return (
    <PainelLayout>
      <div className="space-y-5 p-5">
        <AvisoDaIA />
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Clientes</h1>
            <p className="mt-1 text-[12px] text-white/50">
              A base de quem já passou pelo escritório.
              {total !== null && <> {total} cadastro{total === 1 ? "" : "s"}.</>}
            </p>
          </div>
          <button onClick={() => setNovo({ nome: "" })}
            className="rounded-lg bg-[#C9A24D] px-4 py-2 text-sm font-bold text-[#0A1628]">
            Cadastrar cliente
          </button>
        </div>

        {/* QUEM FAZ ANIVERSÁRIO HOJE, ANTES DE A MENSAGEM SAIR
            Ver a lista é o que permite corrigir um cadastro errado antes
            do disparo das 9h, e não depois. */}
        {hoje.length > 0 && (
          <div className="rounded-xl border border-[#C9A24D]/30 bg-[#C9A24D]/5 p-4">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#C9A24D]">
              Aniversariantes de hoje
            </p>
            <div className="mt-2 space-y-1">
              {hoje.map((a: any) => (
                <p key={comoTexto(a.id)} className="text-[12px] text-white/70">
                  {a.vai_receber ? "✓" : "—"} {comoTexto(a.nome)}
                  {!a.vai_receber && a.motivo && (
                    <span className="text-white/40"> · {comoTexto(a.motivo)}</span>
                  )}
                </p>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-white/40">
              A felicitação sai sozinha às 9h, uma vez por ano para cada pessoa.
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <input value={busca} onChange={(e) => { setBusca(e.target.value); setPagina(0); }}
            placeholder="nome, CPF, e-mail ou WhatsApp"
            className={`${cx} min-w-[240px] flex-1`} />
          <select value={mes} onChange={(e) => { setMes(Number(e.target.value)); setPagina(0); }}
            className={cx}>
            <option value={0}>aniversário: todos os meses</option>
            {MESES.map((m, i) => (
              <option key={m} value={i + 1}>aniversário em {m}</option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-[12px] text-white/60">
            <input type="checkbox" checked={semNascimento}
              onChange={(e) => { setSemNascimento(e.target.checked); setPagina(0); }} />
            sem data de nascimento
          </label>
          <label className="flex items-center gap-1.5 text-[12px] text-white/60">
            <input type="checkbox" checked={descadastrados}
              onChange={(e) => { setDescadastrados(e.target.checked); setPagina(0); }} />
            pediram para não receber
          </label>
        </div>

        {semData > 0 && !semNascimento && (
          <p className="text-[12px] text-[#E5A44C]">
            {semData} nesta página sem data de nascimento. Sem a data, a
            felicitação não tem como sair.
          </p>
        )}

        {erro && (
          <p className="rounded-lg bg-[#E57373]/10 px-3 py-2 text-[12px] leading-relaxed text-[#E57373]">
            {erro}
          </p>
        )}

        {aviso && (
          <p className="rounded-lg border border-[#E5A44C]/30 bg-[#E5A44C]/5 px-3 py-2 text-[12px] leading-relaxed text-[#E5A44C]">
            {aviso}
          </p>
        )}

        {carregando ? (
          <p className="text-sm text-white/40">Carregando a base…</p>
        ) : lista.length === 0 ? (
          <p className="text-sm text-white/40">Nenhum cliente com esses filtros.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-left text-[12px]">
              <thead className="bg-white/5 text-[11px] uppercase tracking-wide text-white/45">
                <tr>
                  <th className="px-3 py-2">Nome</th>
                  <th className="px-3 py-2">WhatsApp</th>
                  <th className="px-3 py-2">Nascimento</th>
                  <th className="px-3 py-2">Relacionamento</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((c: any) => {
                  const fora = !!c.descadastrado_em;
                  return (
                    <tr key={comoTexto(c.id)} className="border-t border-white/5">
                      <td className="px-3 py-2">
                        <p className="font-semibold text-white/85">{comoTexto(c.nome)}</p>
                        <p className="text-[11px] text-white/35">
                          {comoTexto(c.email) || "sem e-mail"}
                          {c.origem ? ` · ${comoTexto(c.origem)}` : ""}
                        </p>
                      </td>
                      <td className="px-3 py-2 font-mono text-white/70">
                        {comoTexto(c.whatsapp) || <span className="text-white/25">—</span>}
                      </td>
                      <td className="px-3 py-2 text-white/70">
                        {c.data_nascimento
                          ? comoTexto(c.data_nascimento).slice(0, 10).split("-").reverse().join("/")
                          : <span className="text-[#E5A44C]">falta</span>}
                      </td>
                      <td className="px-3 py-2">
                        {fora ? (
                          <button onClick={() => mudar(c.id, { descadastrar: false })}
                            className="rounded border border-white/20 px-2 py-1 text-[11px] text-white/60">
                            pediu para sair · religar
                          </button>
                        ) : (
                          <div className="flex flex-wrap items-center gap-2">
                            <label className="flex items-center gap-1 text-[11px] text-white/60">
                              <input type="checkbox"
                                checked={c.aceita_felicitacoes !== false}
                                onChange={(e) => mudar(c.id, { aceita_felicitacoes: e.target.checked })} />
                              felicitações
                            </label>
                            <label className="flex items-center gap-1 text-[11px] text-white/60">
                              <input type="checkbox"
                                checked={!!c.aceita_informativos}
                                onChange={(e) => mudar(c.id, {
                                  aceita_informativos: e.target.checked,
                                  motivo: "autorizado pela equipe na tela de clientes",
                                })} />
                              informativos
                            </label>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center gap-2">
          <button onClick={() => setPagina(Math.max(pagina - 1, 0))} disabled={pagina === 0}
            className="rounded border border-white/15 px-3 py-1.5 text-[12px] text-white/60 disabled:opacity-30">
            anterior
          </button>
          <span className="text-[12px] text-white/40">página {pagina + 1}</span>
          <button onClick={() => setPagina(pagina + 1)} disabled={lista.length < 50}
            className="rounded border border-white/15 px-3 py-1.5 text-[12px] text-white/60 disabled:opacity-30">
            próxima
          </button>
        </div>

        <p className="text-[11px] leading-relaxed text-white/35">
          A felicitação de aniversário sai pelo WhatsApp às 9h, uma vez por
          ano para cada pessoa, e só para quem tem o campo ligado. Quem pede
          para não receber sai de tudo e não volta sozinho.
        </p>
      </div>

      {novo && <NovoCliente aoFechar={() => setNovo(null)} aoSalvar={() => { setNovo(null); carregar(); }} />}
    </PainelLayout>
  );
}

/* ── Cadastro de quem já é cliente e nunca passou pela plataforma ── */
function NovoCliente({ aoFechar, aoSalvar }: { aoFechar: () => void; aoSalvar: () => void }) {
  const [f, setF] = useState<any>({ nome: "", cpf_cnpj: "", whatsapp: "", email: "", data_nascimento: "", relacionamento_nota: "" });
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function salvar() {
    setErro(""); setOcupado(true);
    try {
      const r = await fetch(`${API}/api/v1/clientes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(f),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) setErro(j?.detail || "Não consegui cadastrar.");
      else aoSalvar();
    } catch { setErro("Falha de conexão."); }
    setOcupado(false);
  }

  const cx = "w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A24D]";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={aoFechar}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0F2A44] p-5">
        <h2 className="text-base font-bold text-white">Cadastrar cliente</h2>
        <p className="mt-1 text-[12px] leading-relaxed text-white/50">
          Para quem já é cliente do escritório e nunca passou pela plataforma.
          O sistema recusa se já houver cadastro com o mesmo CPF ou WhatsApp.
        </p>

        <div className="mt-4 space-y-2">
          <input value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })}
            placeholder="nome completo" className={cx} />
          <input value={f.cpf_cnpj} onChange={(e) => setF({ ...f, cpf_cnpj: e.target.value })}
            placeholder="CPF ou CNPJ" className={cx} />
          <input value={f.whatsapp} onChange={(e) => setF({ ...f, whatsapp: e.target.value })}
            placeholder="WhatsApp com DDD" className={cx} />
          <input value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })}
            placeholder="e-mail (opcional)" className={cx} />
          <label className="block text-[11px] text-white/45">data de nascimento</label>
          <input type="date" value={f.data_nascimento}
            onChange={(e) => setF({ ...f, data_nascimento: e.target.value })} className={cx} />
          <input value={f.relacionamento_nota}
            onChange={(e) => setF({ ...f, relacionamento_nota: e.target.value })}
            placeholder="nota (opcional): como o escritório conheceu" className={cx} />
        </div>

        {erro && (
          <p className="mt-3 rounded-lg bg-[#E57373]/10 px-3 py-2 text-[12px] text-[#E57373]">{erro}</p>
        )}

        <div className="mt-4 flex gap-2">
          <button onClick={aoFechar}
            className="flex-1 rounded-lg border border-white/15 px-4 py-2.5 text-sm text-white/70">
            Cancelar
          </button>
          <button onClick={salvar} disabled={ocupado || f.nome.trim().length < 3}
            className="flex-1 rounded-lg bg-[#C9A24D] px-4 py-2.5 text-sm font-bold text-[#0A1628] disabled:opacity-40">
            {ocupado ? "Salvando…" : "Cadastrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
