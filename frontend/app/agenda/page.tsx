"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import PainelLayout from "../components/PainelLayout";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* AGENDA — o dia do escritório, inteiro.

   Antes esta tela desenhava o mês a partir de `prazos`: mostrava só o
   que nasce de intimação. Faltava tudo o mais que ocupa o dia — a
   audiência designada por telefone, a reunião, o atendimento combinado
   no chat, e o recado ("cartório não atende hoje") que não é
   compromisso nenhum mas explica o dia para quem olhar depois.

   Clicar num dia abre o dia: compromissos, notas e o fechamento. É de
   onde se marca, se remarca, se convida e se encerra. */

const SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

const TIPOS = [
  { v: "AUDIENCIA", l: "Audiência", cor: "#C0392B", ico: "⚖️" },
  { v: "PERICIA", l: "Perícia", cor: "#8E44AD", ico: "🔬" },
  { v: "ATENDIMENTO", l: "Atendimento", cor: "#2D7DD2", ico: "💬" },
  { v: "REUNIAO", l: "Reunião", cor: "#16A085", ico: "🤝" },
  { v: "PRAZO", l: "Prazo", cor: "#E5A44C", ico: "⏳" },
  { v: "TAREFA", l: "Tarefa", cor: "#7F8C8D", ico: "✅" },
  { v: "EVENTO", l: "Evento", cor: "#8899AA", ico: "📌" },
];
const doTipo = (t: string) => TIPOS.find((x) => x.v === t) || TIPOS[6];

/* Data curta, no formato de quem lê. `slice` em vez de `new Date` no
   dia inteiro: o fuso transformaria 01/10 em 30/09 à noite. */
const brData = (iso: string) =>
  iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}` : "";

const inp = "w-full rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-sm text-white outline-none focus:border-[#C9A24D]";
const btn = "rounded-lg px-3 py-2 text-xs font-bold transition";

/* Data local, sem UTC. `toISOString()` num fuso negativo devolve o dia
   anterior depois das 21h — e a agenda mostrava o dia errado à noite. */
const fmt = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const brDia = (s: string) => `${s.slice(8, 10)}/${s.slice(5, 7)}`;
const brCompleto = (s: string) =>
  `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;

export default function AgendaPage() {
  const [ref, setRef] = useState(new Date());
  const [itens, setItens] = useState<any[]>([]);
  const [notas, setNotas] = useState<any[]>([]);
  const [fechados, setFechados] = useState<any[]>([]);
  const [membros, setMembros] = useState<any[]>([]);
  const [porResponsavel, setPorResponsavel] = useState("");
  const [diaAberto, setDiaAberto] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const primeiro = useMemo(
    () => new Date(ref.getFullYear(), ref.getMonth(), 1), [ref]);
  const ultimo = useMemo(
    () => new Date(ref.getFullYear(), ref.getMonth() + 1, 0), [ref]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    const de = fmt(primeiro), ate = fmt(ultimo);
    try {
      const p = new URLSearchParams({ de, ate });
      if (porResponsavel) p.set("responsavel_id", porResponsavel);
      const [a, n, f] = await Promise.all([
        fetch(`${API}/api/v1/agenda?${p}`).then((r) => r.json()),
        fetch(`${API}/api/v1/agenda/notas?de=${de}&ate=${ate}`).then((r) => r.json()),
        fetch(`${API}/api/v1/agenda/semana?de=${de}&dias=${ultimo.getDate()}`).then((r) => r.json()),
      ]);
      setItens(Array.isArray(a) ? a : []);
      setNotas(Array.isArray(n) ? n : []);
      setFechados((f?.dias || []).filter((d: any) => d.fechado).map((d: any) => d.fechado));
    } catch {
      setErro("Não consegui carregar a agenda.");
    } finally {
      setCarregando(false);
    }
  }, [primeiro, ultimo, porResponsavel]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    fetch(`${API}/api/v1/membros`).then((r) => r.json())
      .then((d) => setMembros(Array.isArray(d) ? d : [])).catch(() => {});
    // Link direto para um dia: /agenda?dia=2026-09-30 (é o que os
    // e-mails de notificação mandam).
    const q = new URLSearchParams(window.location.search).get("dia");
    if (q) { setDiaAberto(q); setRef(new Date(q + "T12:00:00")); }
  }, []);

  const dias = useMemo(() => {
    const arr: (Date | null)[] = [];
    for (let i = 0; i < primeiro.getDay(); i++) arr.push(null);
    for (let d = 1; d <= ultimo.getDate(); d++)
      arr.push(new Date(ref.getFullYear(), ref.getMonth(), d));
    return arr;
  }, [ref, primeiro, ultimo]);

  const doDia = (d: string) => itens.filter((i) => String(i.data).slice(0, 10) === d);
  const notasDo = (d: string) => notas.filter((n) => String(n.data).slice(0, 10) === d);
  const fechadoEm = (d: string) => fechados.find((f) => String(f.data).slice(0, 10) === d);

  const hoje = fmt(new Date());
  const mover = (n: number) =>
    setRef(new Date(ref.getFullYear(), ref.getMonth() + n, 1));

  return (
    <PainelLayout titulo="Agenda">
      <div className="space-y-4 p-5">
        {/* Cabeçalho */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1">
            <button onClick={() => mover(-1)}
              className={`${btn} border border-white/15 text-white/70 hover:text-white`}>←</button>
            <h2 className="min-w-52 text-center text-sm font-bold capitalize text-[#C9A24D]">
              {MESES[ref.getMonth()]} de {ref.getFullYear()}
            </h2>
            <button onClick={() => mover(1)}
              className={`${btn} border border-white/15 text-white/70 hover:text-white`}>→</button>
            <button onClick={() => setRef(new Date())}
              className={`${btn} ml-1 border border-white/15 text-white/60 hover:text-white`}>hoje</button>
          </div>

          <select value={porResponsavel} onChange={(e) => setPorResponsavel(e.target.value)}
            className="rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-xs text-white outline-none">
            <option value="">Todos os responsáveis</option>
            {membros.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
          </select>

          <button onClick={() => setDiaAberto(hoje)}
            className={`${btn} ml-auto bg-[#C9A24D] text-[#0A1628] hover:brightness-110`}>
            + Novo compromisso
          </button>
          <AssinarCalendario />
        </div>

        {erro && <p className="rounded-lg bg-[#C0392B]/20 px-3 py-2 text-xs text-[#ffb3aa]">{erro}</p>}

        {/* Legenda */}
        <div className="flex flex-wrap gap-3 text-[11px] text-white/45">
          {TIPOS.map((t) => (
            <span key={t.v} className="flex items-center gap-1">
              <i className="inline-block h-2 w-2 rounded-full" style={{ background: t.cor }} />
              {t.l}
            </span>
          ))}
        </div>

        {/* Calendário do mês */}
        <div className="overflow-hidden rounded-xl border border-white/10 bg-[#0B1F3B]">
          <div className="grid grid-cols-7 border-b border-white/10">
            {SEMANA.map((s) => (
              <div key={s} className="px-2 py-2 text-center text-[11px] font-bold text-white/40">{s}</div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {dias.map((d, i) => {
              if (!d) return <div key={i} className="min-h-28 border-b border-r border-white/5 bg-black/10" />;
              const s = fmt(d);
              const lista = doDia(s);
              const nts = notasDo(s);
              const fech = fechadoEm(s);
              const ehHoje = s === hoje;
              const fds = d.getDay() === 0 || d.getDay() === 6;
              return (
                <button key={i} onClick={() => setDiaAberto(s)}
                  className={`min-h-28 border-b border-r border-white/5 p-1.5 text-left align-top transition hover:bg-white/5
                    ${fds ? "bg-black/20" : ""} ${fech?.bloqueia_novos ? "bg-[#C0392B]/10" : ""}`}>
                  <div className="mb-1 flex items-center gap-1">
                    <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold
                      ${ehHoje ? "bg-[#C9A24D] text-[#0A1628]" : "text-white/60"}`}>
                      {d.getDate()}
                    </span>
                    {fech && (
                      <span title={fech.bloqueia_novos ? "Dia bloqueado" : "Dia fechado"}
                        className="text-[10px]">{fech.bloqueia_novos ? "🚫" : "🔒"}</span>
                    )}
                    {nts.length > 0 && <span className="text-[10px]" title={`${nts.length} nota(s)`}>📝</span>}
                  </div>
                  <div className="space-y-0.5">
                    {lista.slice(0, 3).map((it) => {
                      const t = doTipo(it.tipo);
                      return (
                        <div key={it.id}
                          className={`truncate rounded px-1 py-0.5 text-[10px] leading-tight
                            ${it.status === "REALIZADO" ? "opacity-40 line-through" : ""}`}
                          style={{ background: `${t.cor}22`, color: "#fff" }}>
                          {String(it.hora_inicio || "").slice(0, 5)} {it.titulo}
                        </div>
                      );
                    })}
                    {lista.length > 3 && (
                      <div className="px-1 text-[10px] text-white/40">+{lista.length - 3}</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
        {carregando && <p className="text-xs text-white/40">Carregando…</p>}
      </div>

      {diaAberto && (
        <PainelDoDia dia={diaAberto} membros={membros}
          fechar={() => setDiaAberto(null)} recarregar={carregar} />
      )}
    </PainelLayout>
  );
}

/* ── O endereço do calendário assinável ───────────────────────────
   Assinar não é importar: o Google relê o endereço sozinho, então o que
   muda aqui aparece lá sem ninguém reenviar nada. */
function AssinarCalendario() {
  const [aberto, setAberto] = useState(false);
  const [token, setToken] = useState("");
  const url = token
    ? `${API}/api/v1/agenda/feed/${token}.ics`
    : "";
  return (
    <>
      <button onClick={() => setAberto(true)}
        className={`${btn} border border-white/15 text-white/70 hover:text-white`}>
        📅 Google Calendar
      </button>
      {aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setAberto(false)}>
          <div className="w-full max-w-lg rounded-xl border border-white/10 bg-[#0B1F3B] p-5"
            onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-2 text-sm font-bold text-[#C9A24D]">Ver esta agenda no Google Calendar</h3>
            <p className="mb-3 text-xs leading-relaxed text-white/60">
              O Google (e o Outlook, e o iPhone) assina um endereço e relê sozinho de
              tempos em tempos. O que mudar aqui aparece lá sem reenviar nada.
              Cole o token do servidor (<code className="text-white/80">AGENDA_FEED_TOKEN</code>)
              para montar o endereço.
            </p>
            <input value={token} onChange={(e) => setToken(e.target.value.trim())}
              placeholder="token do calendário" className={inp} />
            {url && (
              <div className="mt-3 rounded-lg bg-black/30 p-3">
                <p className="break-all text-[11px] text-white/70">{url}</p>
                <button onClick={() => navigator.clipboard?.writeText(url)}
                  className={`${btn} mt-2 bg-[#C9A24D] text-[#0A1628]`}>Copiar endereço</button>
              </div>
            )}
            <p className="mt-3 text-[11px] leading-relaxed text-white/45">
              No Google Calendar: <b>Outras agendas → + → De URL</b> e cole o endereço.
              Quem tiver este endereço vê a agenda inteira — se vazar, troque o
              token no servidor e as assinaturas antigas param de funcionar.
            </p>
            <button onClick={() => setAberto(false)}
              className={`${btn} mt-4 w-full border border-white/15 text-white/70`}>Fechar</button>
          </div>
        </div>
      )}
    </>
  );
}

/* ── O dia aberto ─────────────────────────────────────────────── */
function PainelDoDia({ dia, membros, fechar, recarregar }:
  { dia: string; membros: any[]; fechar: () => void; recarregar: () => void }) {
  const [d, setD] = useState<any>(null);
  const [aba, setAba] = useState<"lista" | "novo">("lista");
  const [msg, setMsg] = useState("");
  const [nota, setNota] = useState("");

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/agenda/dia/${dia}`);
      setD(await r.json());
    } catch { setMsg("Não consegui abrir o dia."); }
  }, [dia]);
  useEffect(() => { carregar(); }, [carregar]);

  const atualizar = async () => { await carregar(); recarregar(); };

  async function acao(url: string, body: any, ok: string) {
    setMsg("");
    try {
      const r = await fetch(`${API}${url}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setMsg(j?.detail || "Não deu certo."); return false; }
      setMsg(ok);
      await atualizar();
      return true;
    } catch { setMsg("Falha de conexão."); return false; }
  }

  const fech = d?.fechado;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={fechar}>
      <div className="h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-[#0A1628] p-5"
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-base font-bold text-white">{brCompleto(dia)}</h2>
            <p className="text-xs text-white/45">
              {d ? `${d.itens?.length || 0} compromisso(s) · ${d.notas?.length || 0} nota(s)` : "carregando…"}
            </p>
          </div>
          <button onClick={fechar} className="text-xl text-white/40 hover:text-white">×</button>
        </div>

        {/* Estado do dia */}
        {fech && (
          <div className="mb-4 rounded-lg border border-white/10 bg-[#0B1F3B] p-3">
            <p className="text-xs text-white/80">
              {fech.bloqueia_novos ? "🚫 Dia bloqueado para novos agendamentos." : "🔒 Dia fechado (conferido)."}
              {fech.motivo ? ` ${fech.motivo}` : ""}
            </p>
            <button
              onClick={async () => {
                await fetch(`${API}/api/v1/agenda/fechar-dia/${dia}`, { method: "DELETE" });
                atualizar();
              }}
              className={`${btn} mt-2 border border-white/15 text-white/70 hover:text-white`}>
              Reabrir o dia
            </button>
          </div>
        )}

        <div className="mb-4 flex gap-2">
          <button onClick={() => setAba("lista")}
            className={`${btn} ${aba === "lista" ? "bg-[#C9A24D] text-[#0A1628]" : "border border-white/15 text-white/60"}`}>
            O dia
          </button>
          <button onClick={() => setAba("novo")}
            className={`${btn} ${aba === "novo" ? "bg-[#C9A24D] text-[#0A1628]" : "border border-white/15 text-white/60"}`}>
            + Marcar
          </button>
          {!fech && (
            <FecharDiaBotao dia={dia} depois={atualizar} />
          )}
        </div>

        {msg && <p className="mb-3 rounded-lg bg-white/5 px-3 py-2 text-xs text-white/80">{msg}</p>}

        {aba === "novo" ? (
          <FormNovo dia={dia} membros={membros}
            depois={async () => { setAba("lista"); await atualizar(); }} />
        ) : (
          <div className="space-y-4">
            {/* Compromissos */}
            <div className="space-y-2">
              {(d?.itens || []).length === 0 && (
                <p className="text-xs text-white/40">Nada marcado neste dia.</p>
              )}
              {(d?.itens || []).map((it: any) => (
                <Compromisso key={it.id} it={it} membros={membros} acao={acao} />
              ))}
            </div>

            {/* Notas do dia */}
            <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
              <h3 className="mb-2 text-xs font-bold text-[#C9A24D]">Notas do dia</h3>
              <div className="mb-2 space-y-1">
                {(d?.notas || []).length === 0 && (
                  <p className="text-[11px] text-white/35">
                    Sem notas. Aqui vai o que explica o dia e não é compromisso:
                    “cartório não atende”, “perita remarcou por telefone”.
                  </p>
                )}
                {(d?.notas || []).map((n: any) => (
                  <div key={n.id} className="flex items-start gap-2 rounded-lg bg-black/25 px-2 py-1.5">
                    <p className="flex-1 whitespace-pre-line text-[11px] leading-relaxed text-white/80">{n.texto}</p>
                    <button
                      onClick={async () => {
                        await fetch(`${API}/api/v1/agenda/notas/${n.id}`, { method: "DELETE" });
                        atualizar();
                      }}
                      className="text-white/25 hover:text-[#C0392B]">×</button>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input value={nota} onChange={(e) => setNota(e.target.value)}
                  placeholder="escrever uma nota para este dia…" className={inp} />
                <button
                  onClick={async () => {
                    if (!nota.trim()) return;
                    await fetch(`${API}/api/v1/agenda/notas`, {
                      method: "POST", headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ data: dia, texto: nota }),
                    });
                    setNota(""); atualizar();
                  }}
                  className={`${btn} shrink-0 bg-[#C9A24D] text-[#0A1628]`}>Anotar</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function FecharDiaBotao({ dia, depois }: { dia: string; depois: () => void }) {
  const [aberto, setAberto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [bloqueia, setBloqueia] = useState(false);
  return (
    <>
      <button onClick={() => setAberto(true)}
        className={`${btn} ml-auto border border-white/15 text-white/60 hover:text-white`}>
        🔒 Fechar agenda
      </button>
      {aberto && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4"
          onClick={() => setAberto(false)}>
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0B1F3B] p-5"
            onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-1 text-sm font-bold text-[#C9A24D]">Fechar o dia {brDia(dia)}</h3>
            <p className="mb-3 text-[11px] leading-relaxed text-white/55">
              Fechar é dizer que o dia foi conferido e nada ficou para trás.
              Bloquear é outra coisa: não aceitar agendamento nesta data —
              feriado, viagem, júri. Dá para fechar sem bloquear.
            </p>
            <input value={motivo} onChange={(e) => setMotivo(e.target.value)}
              placeholder="motivo (opcional)" className={inp} />
            <label className="mt-3 flex items-center gap-2 text-xs text-white/70">
              <input type="checkbox" checked={bloqueia}
                onChange={(e) => setBloqueia(e.target.checked)} />
              bloquear novos agendamentos nesta data
            </label>
            <div className="mt-4 flex gap-2">
              <button
                onClick={async () => {
                  await fetch(`${API}/api/v1/agenda/fechar-dia`, {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ data: dia, motivo, bloqueia_novos: bloqueia }),
                  });
                  setAberto(false); depois();
                }}
                className={`${btn} flex-1 bg-[#C9A24D] text-[#0A1628]`}>Fechar o dia</button>
              <button onClick={() => setAberto(false)}
                className={`${btn} border border-white/15 text-white/60`}>Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Compromisso({ it, membros, acao }:
  { it: any; membros: any[]; acao: (u: string, b: any, o: string) => Promise<any> }) {
  const [abrir, setAbrir] = useState(false);
  const [novaData, setNovaData] = useState(String(it.data).slice(0, 10));
  const [novaHora, setNovaHora] = useState(String(it.hora_inicio || "").slice(0, 5));
  const [motivo, setMotivo] = useState("");
  const [resultado, setResultado] = useState("");
  const [convEmail, setConvEmail] = useState("");
  const [convNome, setConvNome] = useState("");
  const t = doTipo(it.tipo);
  const convidados = it.agenda_convidados || [];

  /* O DIA EM QUE NÃO DÁ MAIS
   *
   * A data do compromisso é quando se pretende fazer. O prazo fatal é
   * quando deixa de ser possível. A tela mostrava só a primeira, e com
   * isso quem via um prazo marcado para amanhã não sabia se tinha mais
   * uma semana de folga ou se amanhã era o fim.
   *
   * A contagem é em dias de calendário, do dia de hoje até o fatal.
   * Zero é hoje, negativo é vencido, e os dois têm cor própria porque
   * ler "0 dias" e entender "ainda dá" é fácil demais. */
  const fatal = it.prazo_fatal ? String(it.prazo_fatal).slice(0, 10) : "";

  /* O PRAZO QUE SE CONTA EM HORAS
   *
   * Prazo processual é dia: ou dá, ou não dá, e a hora não muda nada.
   * Prazo de serviço é hora: entrega contratada às 14h vence às 14h, e
   * mostrar só o dia dá ao escritório uma folga que ele não tem.
   *
   * Quando o compromisso traz `prazo_fatal_em`, é ele que manda, e a
   * contagem passa a ser em horas enquanto faltar menos de um dia. */
  const fatalHora = it.prazo_fatal_em ? new Date(it.prazo_fatal_em) : null;
  const horasAteFatal = fatalHora
    ? (fatalHora.getTime() - Date.now()) / 3600000 : null;

  const diasAteFatal = (() => {
    if (!fatal) return null;
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    const d = new Date(`${fatal}T00:00:00`);
    return Math.round((d.getTime() - hoje.getTime()) / 86400000);
  })();

  const horaCurta = fatalHora
    ? fatalHora.toLocaleString("pt-BR",
        { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
    : "";

  /* O PRAZO PARADO NÃO É PRAZO ESQUECIDO
   *
   * Enquanto falta informação do cliente, o relógio da entrega fica
   * suspenso e o vencimento anda junto com a espera. Sem dizer isso na
   * tela, quem olha vê um prazo que não se move e conclui que está
   * largado, quando o correto é o contrário: ele está parado porque a
   * bola não está com o escritório. */
  const avisoFatal =
    it.aguardando_cliente
      ? { texto: `parado, esperando o cliente${horaCurta ? ` · retomando vence ${horaCurta}` : ""}`,
          cor: "#8899AA" }
    : horasAteFatal !== null
      ? horasAteFatal < 0
        ? { texto: `prazo venceu ${horaCurta}`, cor: "#C0392B" }
        : horasAteFatal < 1
        ? { texto: `vence em menos de 1 hora, ${horaCurta}`, cor: "#C0392B" }
        : horasAteFatal < 6
        ? { texto: `faltam ${Math.floor(horasAteFatal)}h, vence ${horaCurta}`, cor: "#C0392B" }
        : horasAteFatal < 24
        ? { texto: `faltam ${Math.floor(horasAteFatal)}h, vence ${horaCurta}`, cor: "#E5A44C" }
        : { texto: `entrega até ${horaCurta}`, cor: "#8899AA" }
    : diasAteFatal === null ? null
    : diasAteFatal < 0 ? { texto: `fatal venceu em ${brData(fatal)}`, cor: "#C0392B" }
    : diasAteFatal === 0 ? { texto: "último dia, o fatal é hoje", cor: "#C0392B" }
    : diasAteFatal === 1 ? { texto: `fatal amanhã, ${brData(fatal)}`, cor: "#E5A44C" }
    : diasAteFatal <= 3 ? { texto: `fatal em ${diasAteFatal} dias, ${brData(fatal)}`, cor: "#E5A44C" }
    : { texto: `fatal em ${diasAteFatal} dias, ${brData(fatal)}`, cor: "#8899AA" };

  return (
    <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3"
      style={{ borderLeft: `3px solid ${t.cor}` }}>
      <button onClick={() => setAbrir(!abrir)} className="w-full text-left">
        <div className="flex items-start gap-2">
          <span className="text-sm">{t.ico}</span>
          <div className="min-w-0 flex-1">
            <p className={`truncate text-sm font-semibold text-white ${it.status === "REALIZADO" ? "line-through opacity-50" : ""}`}>
              {String(it.hora_inicio || "").slice(0, 5)} {it.titulo}
            </p>
            <p className="truncate text-[11px] text-white/45">
              {t.l}
              {it.clientes?.nome ? ` · ${it.clientes.nome}` : ""}
              {it.local ? ` · ${it.local}` : ""}
              {it.membros_equipe?.nome ? ` · ${it.membros_equipe.nome}` : ""}
              {it.adiamentos > 0 ? ` · remarcado ${it.adiamentos}×` : ""}
            </p>
            {avisoFatal && it.status !== "REALIZADO" && (
              <p className="mt-1 inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-bold"
                style={{ color: avisoFatal.cor,
                         background: `${avisoFatal.cor}1f` }}>
                <span className="h-1.5 w-1.5 rounded-full"
                  style={{ background: avisoFatal.cor }} />
                {avisoFatal.texto}
              </p>
            )}
          </div>
          <span className="text-white/30">{abrir ? "▴" : "▾"}</span>
        </div>
      </button>

      {abrir && (
        <div className="mt-3 space-y-3 border-t border-white/10 pt-3">
          {it.descricao && (
            <p className="whitespace-pre-line text-[11px] leading-relaxed text-white/60">{it.descricao}</p>
          )}
          {(it.casos?.numero_processo || it.numero_processo) && (
            <p className="text-[11px] text-white/40">
              Processo: {it.casos?.numero_processo || it.numero_processo}
            </p>
          )}

          {/* Convidados */}
          <div>
            <p className="mb-1 text-[11px] font-bold text-white/60">Convidados</p>
            {convidados.length === 0 && <p className="text-[11px] text-white/35">Ninguém convidado.</p>}
            {convidados.map((c: any) => (
              <div key={c.id} className="flex items-center gap-2 text-[11px] text-white/70">
                <span className={c.resposta === "ACEITO" ? "text-[#1DB954]"
                  : c.resposta === "RECUSADO" ? "text-[#C0392B]" : "text-white/30"}>
                  {c.resposta === "ACEITO" ? "✓" : c.resposta === "RECUSADO" ? "✕" : "…"}
                </span>
                <span className="truncate">{c.nome || c.email}</span>
                <span className="text-white/25">{c.papel}</span>
              </div>
            ))}
            <div className="mt-2 flex gap-1">
              <input value={convNome} onChange={(e) => setConvNome(e.target.value)}
                placeholder="nome" className={`${inp} py-1 text-[11px]`} />
              <input value={convEmail} onChange={(e) => setConvEmail(e.target.value)}
                placeholder="e-mail" className={`${inp} py-1 text-[11px]`} />
              <button
                onClick={async () => {
                  if (!convEmail.includes("@")) return;
                  await acao(`/api/v1/agenda/${it.id}/convidar`,
                    { email: convEmail, nome: convNome, papel: "OUTRO" },
                    "Convite enviado.");
                  setConvEmail(""); setConvNome("");
                }}
                className={`${btn} shrink-0 bg-[#2D7DD2] text-white`}>Convidar</button>
            </div>
          </div>

          {/* Responsável */}
          <div className="flex items-center gap-2">
            <select defaultValue={it.responsavel_id || ""}
              onChange={(e) => acao(`/api/v1/agenda/${it.id}/responsavel`,
                { responsavel_id: e.target.value || null }, "Responsável avisado por e-mail.")}
              className={`${inp} py-1 text-[11px]`}>
              <option value="">sem responsável</option>
              {membros.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
            </select>
            {it.responsavel_id && !it.responsavel_avisado_em && (
              <span className="shrink-0 text-[10px] text-[#E5A44C]" title="Designado mas ainda não avisado">
                não avisado
              </span>
            )}
          </div>

          {/* Remarcar */}
          <div className="rounded-lg bg-black/25 p-2">
            <p className="mb-1 text-[11px] font-bold text-white/60">Remarcar</p>
            <div className="flex gap-1">
              <input type="date" value={novaData} onChange={(e) => setNovaData(e.target.value)}
                className={`${inp} py-1 text-[11px]`} />
              <input type="time" value={novaHora} onChange={(e) => setNovaHora(e.target.value)}
                className={`${inp} py-1 text-[11px]`} />
            </div>
            <input value={motivo} onChange={(e) => setMotivo(e.target.value)}
              placeholder="motivo" className={`${inp} mt-1 py-1 text-[11px]`} />
            <button
              onClick={() => acao(`/api/v1/agenda/${it.id}/reagendar`,
                { nova_data: novaData, nova_hora: novaHora || null, motivo },
                "Remarcado. Quem foi convidado recebeu a nova data.")}
              className={`${btn} mt-2 w-full bg-[#E5A44C] text-[#0A1628]`}>
              Remarcar e avisar
            </button>
          </div>

          {/* Concluir / cancelar */}
          {it.status !== "REALIZADO" && it.status !== "CANCELADO" && (
            <div className="space-y-1">
              <input value={resultado} onChange={(e) => setResultado(e.target.value)}
                placeholder="o que aconteceu? (vai para o histórico do cliente)"
                className={`${inp} py-1 text-[11px]`} />
              <div className="flex gap-1">
                {/* Marcar realizado fecha a cadeia inteira: o prazo
                    que este compromisso espelha, a tarefa que o
                    originou e a intimação que o motivou. E o que você
                    escrever acima vira linha no histórico do caso, que
                    é de onde sai a prestação de contas. */}
                <button
                  onClick={() => acao(`/api/v1/agenda/${it.id}/concluir`,
                    { resultado },
                    "Realizado. Prazo, tarefa e intimação ligados a ele "
                    + "foram fechados, e ficou registrado no caso.")}
                  className={`${btn} flex-1 bg-[#1DB954] text-[#0A1628]`}>Realizado</button>
                <button
                  onClick={() => {
                    if (!confirm("Cancelar? Quem foi convidado será avisado.")) return;
                    acao(`/api/v1/agenda/${it.id}/cancelar`, { motivo: resultado },
                      "Cancelado e convidados avisados.");
                  }}
                  className={`${btn} border border-[#C0392B]/50 text-[#ff9c90]`}>Cancelar</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FormNovo({ dia, membros, depois }:
  { dia: string; membros: any[]; depois: () => void }) {
  const [f, setF] = useState<any>({
    tipo: "AUDIENCIA", titulo: "", descricao: "", data: dia,
    hora_inicio: "", hora_fim: "", local: "", link: "",
    numero_processo: "", responsavel_id: "",
  });
  const [convidados, setConvidados] = useState<any[]>([]);
  const [busca, setBusca] = useState("");
  const [achados, setAchados] = useState<any[]>([]);
  const [caso, setCaso] = useState<any>(null);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  const set = (k: string, v: any) => setF((x: any) => ({ ...x, [k]: v }));

  async function procurar() {
    if (busca.trim().length < 3) return;
    try {
      const r = await fetch(`${API}/api/v1/buscar?q=${encodeURIComponent(busca)}`);
      const d = await r.json();
      setAchados(d.casos || []);
    } catch { setAchados([]); }
  }

  async function salvar(forcar = false) {
    setErro(""); setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/agenda`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...f,
          hora_inicio: f.hora_inicio || null,
          hora_fim: f.hora_fim || null,
          responsavel_id: f.responsavel_id || null,
          caso_id: caso?.id || null,
          cliente_id: caso?.cliente_id || null,
          numero_processo: caso?.numero_processo || f.numero_processo || null,
          convidados, forcar,
        }),
      });
      const j = await r.json().catch(() => ({}));
      if (r.status === 409) {
        // Dia bloqueado. Quem está olhando a tela decide, não o sistema.
        if (confirm(`${j?.detail}\n\nMarcar mesmo assim?`)) return salvar(true);
        return;
      }
      if (!r.ok) { setErro(j?.detail || "Não consegui marcar."); return; }
      depois();
    } catch { setErro("Falha de conexão."); }
    finally { setSalvando(false); }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <select value={f.tipo} onChange={(e) => set("tipo", e.target.value)} className={inp}>
          {TIPOS.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}
        </select>
        <select value={f.responsavel_id} onChange={(e) => set("responsavel_id", e.target.value)} className={inp}>
          <option value="">sem responsável</option>
          {membros.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
        </select>
      </div>

      <input value={f.titulo} onChange={(e) => set("titulo", e.target.value)}
        placeholder="do que se trata" className={inp} />

      <div className="grid grid-cols-3 gap-2">
        <input type="date" value={f.data} onChange={(e) => set("data", e.target.value)} className={inp} />
        <input type="time" value={f.hora_inicio} onChange={(e) => set("hora_inicio", e.target.value)} className={inp} />
        <input type="time" value={f.hora_fim} onChange={(e) => set("hora_fim", e.target.value)} className={inp} />
      </div>
      <p className="-mt-1 text-[10px] text-white/35">Sem hora, entra como dia inteiro.</p>

      <input value={f.local} onChange={(e) => set("local", e.target.value)}
        placeholder="onde (fórum, sala, endereço)" className={inp} />
      <input value={f.link} onChange={(e) => set("link", e.target.value)}
        placeholder="link da sala virtual (opcional)" className={inp} />

      {/* Caso */}
      <div className="rounded-lg bg-black/25 p-2">
        <p className="mb-1 text-[11px] font-bold text-white/60">Ligar a um caso</p>
        {caso ? (
          <div className="flex items-center gap-2 text-[11px] text-white/80">
            <span className="flex-1 truncate">
              {caso.clientes?.nome} {caso.numero_processo ? `· ${caso.numero_processo}` : ""}
            </span>
            <button onClick={() => setCaso(null)} className="text-white/30 hover:text-white">×</button>
          </div>
        ) : (
          <>
            <div className="flex gap-1">
              <input value={busca} onChange={(e) => setBusca(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && procurar()}
                placeholder="nome do cliente ou nº do processo" className={`${inp} py-1 text-[11px]`} />
              <button onClick={procurar} className={`${btn} shrink-0 border border-white/15 text-white/70`}>🔍</button>
            </div>
            {achados.slice(0, 5).map((c) => (
              <button key={c.id} onClick={() => { setCaso(c); setAchados([]); }}
                className="mt-1 block w-full truncate rounded px-2 py-1 text-left text-[11px] text-white/70 hover:bg-white/5">
                {c.clientes?.nome ?? "—"} {c.numero_processo ? `· ${c.numero_processo}` : ""}
              </button>
            ))}
          </>
        )}
      </div>

      {/* Convidados */}
      <div className="rounded-lg bg-black/25 p-2">
        <p className="mb-1 text-[11px] font-bold text-white/60">
          Convidar (recebem o convite por e-mail, com botão de confirmar)
        </p>
        {convidados.map((c, i) => (
          <div key={i} className="flex items-center gap-2 text-[11px] text-white/70">
            <span className="flex-1 truncate">{c.nome || c.email}</span>
            <button onClick={() => setConvidados(convidados.filter((_, j) => j !== i))}
              className="text-white/30 hover:text-white">×</button>
          </div>
        ))}
        <NovoConvidado add={(c) => setConvidados([...convidados, c])} cliente={caso?.clientes} />
      </div>

      {erro && <p className="rounded-lg bg-[#C0392B]/20 px-3 py-2 text-xs text-[#ffb3aa]">{erro}</p>}

      <button onClick={() => salvar(false)} disabled={!f.titulo.trim() || salvando}
        className={`${btn} w-full bg-[#C9A24D] py-2.5 text-[#0A1628] disabled:opacity-40`}>
        {salvando ? "Marcando…" : "Marcar na agenda"}
      </button>
    </div>
  );
}

function NovoConvidado({ add, cliente }: { add: (c: any) => void; cliente?: any }) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [papel, setPapel] = useState("OUTRO");
  return (
    <div className="mt-2 space-y-1">
      {cliente?.email && (
        <button onClick={() => add({ nome: cliente.nome, email: cliente.email, papel: "CLIENTE" })}
          className="w-full rounded bg-white/5 px-2 py-1 text-left text-[11px] text-white/70 hover:bg-white/10">
          + convidar o cliente ({cliente.email})
        </button>
      )}
      <div className="flex gap-1">
        <input value={nome} onChange={(e) => setNome(e.target.value)}
          placeholder="nome" className={`${inp} py-1 text-[11px]`} />
        <input value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="e-mail" className={`${inp} py-1 text-[11px]`} />
        <select value={papel} onChange={(e) => setPapel(e.target.value)}
          className={`${inp} w-28 shrink-0 py-1 text-[11px]`}>
          <option value="CLIENTE">Cliente</option>
          <option value="EQUIPE">Equipe</option>
          <option value="PARTE">Parte</option>
          <option value="PERITO">Perito</option>
          <option value="OUTRO">Outro</option>
        </select>
        <button
          onClick={() => {
            if (!email.includes("@")) return;
            add({ nome, email, papel }); setNome(""); setEmail("");
          }}
          className={`${btn} shrink-0 border border-white/15 text-white/70`}>+</button>
      </div>
    </div>
  );
}
