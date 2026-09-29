"use client";
import { useCallback, useEffect, useState } from "react";
import PainelLayout from "../components/PainelLayout";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* EQUIPE
 *
 * A tela que faltava. Para dar acesso a alguém era preciso criar o
 * usuário no painel do Supabase, escrever a linha do membro no banco e
 * trocar o papel na mão: três passos fora da plataforma, feitos por
 * quem tem a chave do projeto, e nenhum deles registrado como decisão
 * de alguém.
 *
 * Duas listas, porque são dois estados diferentes e misturá-los esconde
 * o que importa:
 *
 *   convites   pessoas que receberam o link e ainda não entraram. É a
 *              lista que precisa de ação: reenviar ou cancelar.
 *   equipe     quem já tem acesso. É a lista que se consulta.
 *
 * O nível aparece em toda parte, com o que cada um pode fazer escrito
 * por extenso. Escolher permissão por um nome que ninguém explicou é
 * como assinar sem ler.
 */

type Nivel = {
  id: string; nome: string; papel: string; convidavel: boolean;
  resumo: string; pode?: string[]; nao_pode?: string[];
};

const cx = "w-full rounded-lg border border-white/10 bg-navy px-3 py-2.5 text-small text-white placeholder:text-slate/60 outline-none transition focus:border-electric";

const dataBR = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }) : "";

export default function Equipe() {
  const [dados, setDados] = useState<any>(null);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState("");
  const [quem, setQuem] = useState("");
  const [abrirConvite, setAbrirConvite] = useState(false);

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [nivel, setNivel] = useState("ASSESSOR");
  const [telefone, setTelefone] = useState("");

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/equipe`);
      setDados(await r.json());
    } catch { setErro("Não consegui carregar a equipe."); }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setQuem(data.user?.email || "");
    });
  }, []);

  const niveis: Nivel[] = dados?.niveis || [];
  const escolhido = niveis.find((n) => n.id === nivel);

  async function convidar() {
    setOcupado("convidar"); setErro(""); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/equipe/convites`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome, email, nivel, telefone, quem }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(j?.detail || "Não foi possível convidar."); return; }
      setAviso(j.email_enviado
        ? `Convite enviado para ${email}. O link vale sete dias.`
        : `Convite criado, mas o e-mail não saiu. Envie este link à pessoa: ${j.link}`);
      setNome(""); setEmail(""); setTelefone(""); setAbrirConvite(false);
      carregar();
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(""); }
  }

  async function acao(url: string, rotulo: string, recarrega = true) {
    setOcupado(rotulo); setErro(""); setAviso("");
    try {
      const r = await fetch(url, { method: "POST" });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(j?.detail || "Não deu certo."); return; }
      if (j?.link && j?.email_enviado === false) {
        setAviso(`O e-mail não saiu. Envie este link à pessoa: ${j.link}`);
      }
      if (recarrega) carregar();
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(""); }
  }

  async function mudarNivel(perfilId: string, nomePessoa: string, atual: string) {
    const novo = prompt(
      `Novo nível de ${nomePessoa}.\n\n`
      + niveis.map((n) => `${n.id} = ${n.nome}`).join("\n")
      + `\n\nAtual: ${atual}`, atual);
    if (!novo) return;
    let motivo = "";
    if (novo.toUpperCase() === "ADMINISTRADOR") {
      motivo = prompt(
        "Administrador pode excluir pedido e forçar peticionamento.\n"
        + "Escreva por que esta pessoa passa a administrador:") || "";
      if (!motivo.trim()) return;
    }
    setOcupado("nivel"); setErro(""); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/equipe/perfis/${perfilId}/nivel`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nivel: novo.toUpperCase(), motivo, quem }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(j?.detail || "Não deu certo."); return; }
      setAviso(`${nomePessoa} agora é ${novo.toLowerCase()}.`);
      carregar();
    } finally { setOcupado(""); }
  }

  return (
    <PainelLayout titulo="Equipe">
      <div className="mx-auto max-w-5xl px-5 py-7">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-title font-bold text-white">Equipe</h1>
            <p className="mt-1 max-w-xl text-small text-slate">
              Quem tem acesso à plataforma e quem foi convidado. O convite
              chega por e-mail e a pessoa cria a própria senha: ninguém aqui
              escolhe senha por ela.
            </p>
          </div>
          <button onClick={() => setAbrirConvite(!abrirConvite)}
            className="rounded-lg bg-electric px-5 py-2.5 text-small font-bold text-white transition hover:bg-indigo">
            {abrirConvite ? "Fechar" : "Convidar pessoa"}
          </button>
        </div>

        {erro && (
          <p className="mb-4 rounded-lg border border-crimson/40 bg-crimson/10 px-4 py-2.5 text-small text-white">
            {erro}
          </p>
        )}
        {aviso && (
          <p className="mb-4 break-words rounded-lg border border-emerald/40 bg-emerald/10 px-4 py-2.5 text-small text-white">
            {aviso}
          </p>
        )}

        {/* ── O CONVITE ────────────────────────────────────────── */}
        {abrirConvite && (
          <section className="mb-8 rounded-xl2 border border-white/10 bg-petrol p-6">
            <h2 className="font-display text-body font-bold text-white">
              Convidar para a equipe
            </h2>
            <p className="mt-1 text-small text-slate">
              A pessoa recebe um e-mail de boas-vindas com um link de uso
              único, válido por sete dias.
            </p>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-caption text-slate">Nome completo</span>
                <input value={nome} onChange={(e) => setNome(e.target.value)}
                  className={`mt-1 ${cx}`} placeholder="Como consta no documento" />
              </label>
              <label className="block">
                <span className="text-caption text-slate">E-mail de trabalho</span>
                <input value={email} onChange={(e) => setEmail(e.target.value)}
                  type="email" className={`mt-1 ${cx}`} placeholder="nome@exemplo.com" />
              </label>
              <label className="block">
                <span className="text-caption text-slate">Telefone (opcional)</span>
                <input value={telefone} onChange={(e) => setTelefone(e.target.value)}
                  className={`mt-1 ${cx}`} placeholder="69 99999 0000" />
              </label>
            </div>

            {/* OS NÍVEIS, COM O QUE CADA UM PODE FAZER
                Escolher permissão por um nome que ninguém explicou é
                como assinar sem ler. O administrador aparece na lista,
                marcado, porque escondê-lo faria parecer que não existe. */}
            <p className="mt-6 text-caption font-semibold uppercase tracking-wider text-slate">
              Nível de acesso
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {niveis.map((n) => {
                const ativo = nivel === n.id;
                return (
                  <button key={n.id} type="button"
                    onClick={() => n.convidavel && setNivel(n.id)}
                    disabled={!n.convidavel}
                    className={`rounded-xl2 border p-4 text-left transition ${
                      !n.convidavel
                        ? "cursor-not-allowed border-white/5 bg-navy/40 opacity-60"
                        : ativo
                        ? "border-electric bg-electric/10"
                        : "border-white/10 bg-navy hover:border-white/30"}`}>
                    <div className="flex items-center gap-2">
                      <span className="font-display text-body font-bold text-white">
                        {n.nome}
                      </span>
                      {!n.convidavel && (
                        <span className="rounded-full bg-gold/20 px-2 py-0.5 text-[10px] font-bold text-gold">
                          só por promoção
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-small text-slate">{n.resumo}</p>
                  </button>
                );
              })}
            </div>

            {escolhido && (
              <div className="mt-4 rounded-xl2 border border-white/10 bg-navy p-5">
                <p className="text-caption font-semibold uppercase tracking-wider text-slate">
                  {escolhido.nome} pode
                </p>
                <ul className="mt-2 space-y-1">
                  {(escolhido.pode || []).map((p) => (
                    <li key={p} className="text-small text-white/80">• {p}</li>
                  ))}
                </ul>
                {(escolhido.nao_pode || []).length > 0 && (
                  <>
                    <p className="mt-4 text-caption font-semibold uppercase tracking-wider text-slate">
                      Não pode
                    </p>
                    <ul className="mt-2 space-y-1">
                      {(escolhido.nao_pode || []).map((p) => (
                        <li key={p} className="text-small text-white/55">• {p}</li>
                      ))}
                    </ul>
                  </>
                )}
                <p className="mt-4 text-caption text-slate">
                  Administrador não sai de link de convite. Convite que vaza
                  vira conta com poder total, então a promoção é feita aqui
                  dentro, por alguém já administrador, e fica registrada.
                </p>
              </div>
            )}

            <button onClick={convidar}
              disabled={ocupado === "convidar" || nome.trim().length < 3 || !email.includes("@")}
              className="mt-5 rounded-lg bg-electric px-6 py-3 text-small font-bold text-white transition hover:bg-indigo disabled:opacity-40">
              {ocupado === "convidar" ? "Enviando…" : "Enviar convite"}
            </button>
          </section>
        )}

        {/* ── CONVITES EM ABERTO ───────────────────────────────── */}
        {(dados?.convites || []).length > 0 && (
          <section className="mb-8">
            <h2 className="mb-3 font-display text-body font-bold text-white">
              Convites em aberto
            </h2>
            <div className="space-y-2">
              {dados.convites.map((c: any) => (
                <div key={c.id}
                  className="flex flex-wrap items-center gap-3 rounded-xl2 border border-white/10 bg-petrol p-4">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-small font-semibold text-white">{c.nome}</p>
                    <p className="truncate text-caption text-slate">
                      {c.email} · {(dados.niveis.find((n: Nivel) => n.id === c.nivel) || {}).nome || c.nivel}
                      {c.convidado_por ? ` · convidado por ${c.convidado_por}` : ""}
                    </p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-caption font-bold ${
                    c.status === "EXPIRADO"
                      ? "bg-crimson/15 text-crimson" : "bg-amber/15 text-amber"}`}>
                    {c.status === "EXPIRADO" ? "venceu" : `vence em ${dataBR(c.expira_em)}`}
                  </span>
                  <button onClick={() => acao(`${API}/api/v1/equipe/convites/${c.id}/reenviar?quem=${encodeURIComponent(quem)}`, "reenviar")}
                    className="rounded-lg border border-white/20 px-4 py-2 text-caption font-semibold text-white/85 transition hover:border-white/45">
                    Reenviar
                  </button>
                  <button onClick={() => {
                    if (!confirm(`Cancelar o convite de ${c.nome}? O link deixa de funcionar.`)) return;
                    acao(`${API}/api/v1/equipe/convites/${c.id}/cancelar?quem=${encodeURIComponent(quem)}`, "cancelar");
                  }}
                    className="rounded-lg border border-crimson/40 px-4 py-2 text-caption font-semibold text-crimson transition hover:bg-crimson/10">
                    Cancelar
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── QUEM JÁ ESTÁ ─────────────────────────────────────── */}
        <section>
          <h2 className="mb-3 font-display text-body font-bold text-white">
            Na equipe
          </h2>

          {!dados ? (
            <p className="text-small text-slate">Carregando</p>
          ) : (dados.membros || []).length === 0 ? (
            <p className="rounded-xl2 border border-white/10 bg-petrol p-6 text-small text-slate">
              Ninguém cadastrado ainda. Use o botão de convidar acima.
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl2 border border-white/10">
              {dados.membros.map((m: any, i: number) => (
                <div key={m.id}
                  className={`flex flex-wrap items-center gap-3 bg-petrol p-4 ${
                    i > 0 ? "border-t border-white/5" : ""} ${m.ativo ? "" : "opacity-50"}`}>
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-navy font-display text-small font-bold text-electric">
                    {(m.nome || "?").trim().charAt(0).toUpperCase()}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-small font-semibold text-white">
                      {m.nome}
                      {!m.ativo && <span className="ml-2 text-caption text-slate">desligado</span>}
                    </p>
                    <p className="truncate text-caption text-slate">
                      {m.email || "sem e-mail"}
                      {m.entrou_em ? ` · entrou em ${dataBR(m.entrou_em)}` : ""}
                    </p>
                  </div>

                  <span className="rounded-full bg-white/5 px-3 py-1 text-caption font-semibold text-white/75">
                    {m.nivel_nome || m.nivel}
                  </span>

                  {m.aguardando ? (
                    <span className="text-caption text-amber">aguardando aceite</span>
                  ) : (
                    <button onClick={() => mudarNivel(m.perfil_id, m.nome, m.nivel)}
                      className="rounded-lg border border-white/20 px-4 py-2 text-caption font-semibold text-white/85 transition hover:border-white/45">
                      Mudar nível
                    </button>
                  )}

                  {m.ativo ? (
                    <button onClick={() => {
                      const motivo = prompt(`Desligar ${m.nome}? O acesso é retirado na hora.\n\nMotivo:`);
                      if (motivo === null) return;
                      acao(`${API}/api/v1/equipe/membros/${m.id}/desligar?quem=${encodeURIComponent(quem)}&motivo=${encodeURIComponent(motivo)}`, "desligar");
                    }}
                      className="rounded-lg border border-crimson/40 px-4 py-2 text-caption font-semibold text-crimson transition hover:bg-crimson/10">
                      Desligar
                    </button>
                  ) : (
                    <button onClick={() => acao(`${API}/api/v1/equipe/membros/${m.id}/reativar?quem=${encodeURIComponent(quem)}`, "reativar")}
                      className="rounded-lg border border-white/20 px-4 py-2 text-caption font-semibold text-white/85 transition hover:border-white/45">
                      Reativar
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="mt-4 text-caption text-slate">
            Desligar retira o acesso e mantém o histórico: o nome continua nos
            prazos cumpridos e nas tarefas fechadas, que é justamente o que
            ninguém pode perder.
          </p>
        </section>
      </div>
    </PainelLayout>
  );
}
