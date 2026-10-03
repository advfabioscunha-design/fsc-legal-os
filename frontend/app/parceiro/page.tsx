"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A ÁREA DO ADVOGADO PARCEIRO.
 *
 * Tela própria, de propósito. O caminho mais curto seria mostrar ao
 * parceiro o painel da equipe com menos itens de menu — e é assim que
 * vazamento acontece: basta alguém esquecer de esconder um link, ou o
 * parceiro digitar um endereço, e ele está dentro da carteira inteira.
 *
 * Aqui não há menu do escritório. O que existe nesta tela é o que a
 * parceria dele alcança, e nada mais aparece porque nada mais está
 * escrito aqui.
 *
 * O ESTADO QUE QUASE NINGUÉM DESENHA
 *
 * Entre o cadastro e a aprovação existe um intervalo, e é nele que o
 * advogado chega pela primeira vez. Uma tela vazia nesse momento faz a
 * pessoa achar que deu errado. Então o "em análise" é a tela principal
 * enquanto durar, com o que falta e o que vem depois.
 */

type Eu = {
  id: string; nome: string; oab: string; email: string;
  status: string; em_analise: boolean;
  falta_cadastro: string[]; falta_dados_bancarios: boolean;
  pode_receber: boolean; pode_usar_ia: boolean; pode_falar_com_cliente: boolean;
};

type Caso = {
  id: string; titulo: string; numero_atendimento?: string;
  grupo?: string; estado?: string; numero_processo?: string;
  meu_percentual?: number | null; percentual_aprovado?: boolean;
  atualizado_em?: string;
};

export default function AreaDoParceiro() {
  const router = useRouter();
  const [eu, setEu] = useState<Eu | null>(null);
  const [casos, setCasos] = useState<Caso[]>([]);
  const [valores, setValores] = useState<any>(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  /* MEU CADASTRO
     Os dados bancários saíram da porta de entrada — pedi-los antes do
     primeiro caso é parar o advogado para procurar número de conta num
     momento em que ele só quer entrar. Vivem aqui, onde ele informa
     quando quiser, e onde a cobrança faz sentido: ao lado do valor que
     está esperando para ser repassado. */
  const [abrirCadastro, setAbrirCadastro] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [recado, setRecado] = useState("");
  const [ban, setBan] = useState({
    pix_tipo: "", pix_chave: "", banco_nome: "", banco_codigo: "",
    agencia: "", conta: "", conta_tipo: "", whatsapp: "",
  });

  const buscar = useCallback(async (caminho: string) => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) { router.replace("/entrar"); return null; }
    const r = await fetch(`${API}${caminho}`, {
      headers: { Authorization: `Bearer ${data.session.access_token}` },
    });
    const d = await r.json().catch(() => ({} as any));
    return { ok: r.ok, status: r.status, dados: d };
  }, [router]);

  useEffect(() => {
    (async () => {
      const quem = await buscar("/api/v1/parceiro/eu");
      if (!quem) return;
      if (!quem.ok) {
        /* 404 aqui significa "entrou com uma conta que não tem cadastro
           de parceiro" — quase sempre a conta Google errada. Dizer isso
           evita a suspeita de que o escritório apagou o cadastro. */
        setErro(quem.status === 404
          ? "Não há cadastro de parceiro para esta conta. Se o senhor se "
            + "cadastrou com outro e-mail, entre com ele."
          : (quem.dados?.detail || "Não consegui abrir a sua área."));
        setCarregando(false);
        return;
      }
      setEu(quem.dados);

      /* Em análise não busca caso: não há nenhum, e a chamada só
         voltaria com a mesma recusa que o porteiro já deu. */
      if (!quem.dados.em_analise) {
        const [c, v] = await Promise.all([
          buscar("/api/v1/parceiro/casos"),
          buscar("/api/v1/parceiro/valores"),
        ]);
        if (c?.ok) setCasos(Array.isArray(c.dados) ? c.dados : []);
        if (v?.ok) setValores(v.dados);
      }
      setCarregando(false);
    })();
  }, [buscar]);

  const campo = "rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 "
    + "text-sm text-white outline-none focus:border-[#C9A84C]";

  const reais = (v: any) =>
    Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  async function salvarCadastro() {
    setRecado(""); setSalvando(true);
    try {
      const { data } = await supabase.auth.getSession();
      if (!data.session) { router.replace("/entrar"); return; }
      const r = await fetch(`${API}/api/v1/parceiro/cadastro`, {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   Authorization: `Bearer ${data.session.access_token}` },
        body: JSON.stringify(ban),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { setRecado(d.detail || "Não consegui salvar."); return; }
      setRecado("Dados salvos. O escritório já pode repassar a sua parte.");
      const quem = await buscar("/api/v1/parceiro/eu");
      if (quem?.ok) setEu(quem.dados);
    } catch {
      setRecado("Falha de conexão. Tente de novo.");
    } finally { setSalvando(false); }
  }

  async function sair() {
    await supabase.auth.signOut();
    router.replace("/entrar");
  }

  if (carregando) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A1628] text-sm text-white/60">
        Abrindo a sua área…
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0A1628] px-5 py-8 font-sans text-white">
      <div className="mx-auto max-w-4xl">

        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#C9A84C]">
              FC Advocacia · Área do parceiro
            </p>
            <h1 className="mt-1 font-display text-2xl font-bold">
              {eu?.nome || "Advogado parceiro"}
            </h1>
            {eu?.oab && <p className="text-sm text-white/45">OAB {eu.oab}</p>}
          </div>
          <button onClick={sair}
            className="rounded-lg border border-white/15 px-4 py-2 text-xs text-white/70 transition hover:border-white/40 hover:text-white">
            sair
          </button>
        </header>

        {erro && (
          <p className="mt-6 rounded-xl border border-[#C0392B]/40 bg-[#C0392B]/10 px-4 py-3 text-sm">
            {erro}
          </p>
        )}

        {/* ── EM ANÁLISE ───────────────────────────────────────── */}
        {eu?.em_analise && (
          <section className="mt-6 rounded-2xl border border-[#E5A44C]/30 bg-[#E5A44C]/[0.07] p-6">
            <h2 className="font-display text-lg font-bold text-[#E5A44C]">
              Cadastro em análise
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-white/75">
              O escritório recebeu o seu cadastro e vai conferir a inscrição na
              OAB. Assim que a parceria for aprovada, os casos aparecem aqui —
              e o senhor é avisado.
            </p>
            <p className="mt-3 text-[13px] leading-relaxed text-white/50">
              Enquanto isso, nenhum processo fica visível. Não é falha: é a
              mesma regra que garante que cada parceiro veja apenas as causas
              em que consta o seu nome.
            </p>

            {(eu.falta_cadastro.length > 0 || eu.falta_dados_bancarios) && (
              <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs font-semibold text-white/80">
                  Para adiantar, ainda falta:
                </p>
                <ul className="mt-2 space-y-1 text-[13px] text-white/60">
                  {eu.falta_cadastro.map((c) => (
                    <li key={c}>· {c.replace("_", " ")}</li>
                  ))}
                  {eu.falta_dados_bancarios && (
                    <li>· dados bancários ou chave PIX para o repasse</li>
                  )}
                </ul>
              </div>
            )}
          </section>
        )}

        {/* ── APROVADO: OS VALORES ─────────────────────────────── */}
        {eu && !eu.em_analise && (
          <>
            <section className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
                <p className="text-xs uppercase tracking-wide text-white/40">
                  Já recebido
                </p>
                <p className="mt-1 font-display text-2xl font-bold text-[#1DB954]">
                  {reais(valores?.recebido)}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
                <p className="text-xs uppercase tracking-wide text-white/40">
                  A receber
                </p>
                <p className="mt-1 font-display text-2xl font-bold text-[#C9A84C]">
                  {reais(valores?.a_receber)}
                </p>
              </div>
            </section>

            {!eu.pode_receber && (
              <p className="mt-3 rounded-xl border border-[#E5A44C]/30 bg-[#E5A44C]/[0.07] px-4 py-3 text-[13px] leading-relaxed text-white/70">
                Complete os dados bancários no seu cadastro. O escritório não
                consegue repassar a sua parte sem eles — e o valor fica parado
                esperando um dado que leva um minuto para informar.
              </p>
            )}

            {/* ── OS CASOS ───────────────────────────────────── */}
            <section className="mt-7">
              <h2 className="font-display text-lg font-bold">
                Casos da sua parceria
              </h2>
              <p className="mt-1 text-[13px] text-white/45">
                Só aparecem aqui as causas em que consta o seu nome. Caso
                concluído e arquivado sai da lista; o que o senhor recebeu
                continua no histórico acima.
              </p>

              <ul className="mt-4 space-y-2">
                {casos.map((c) => (
                  <li key={c.id}>
                    <a href={`/parceiro/caso/${c.id}`}
                      className="block rounded-xl border border-white/10 bg-[#0B1F3B] p-4 transition hover:border-white/25">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold">
                          {c.titulo || "Causa sem título"}
                        </span>
                        {c.numero_atendimento && (
                          <span className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px] text-white/55">
                            {c.numero_atendimento}
                          </span>
                        )}
                        {c.meu_percentual != null && (
                          <span className={`ml-auto rounded px-2 py-0.5 text-[11px] font-bold ${
                            c.percentual_aprovado
                              ? "bg-[#1DB954]/15 text-[#1DB954]"
                              : "bg-[#E5A44C]/15 text-[#E5A44C]"}`}>
                            {c.meu_percentual}%
                            {!c.percentual_aprovado && " · a aprovar"}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-[12px] text-white/45">
                        {[c.grupo, c.estado, c.numero_processo]
                          .filter(Boolean).join(" · ")}
                      </p>
                    </a>
                  </li>
                ))}

                {casos.length === 0 && (
                  <li className="rounded-xl border border-white/10 bg-[#0B1F3B] p-6 text-center">
                    <p className="text-sm text-white/55">
                      Ainda não há caso vinculado à sua parceria.
                    </p>
                    <p className="mt-1 text-[12px] text-white/35">
                      Quando o escritório vincular o senhor a uma causa, ela
                      aparece aqui.
                    </p>
                  </li>
                )}
              </ul>
            </section>
          </>
        )}


        {/* ── MEU CADASTRO ─────────────────────────────────────
            Aparece para quem está em análise e para quem já foi
            aprovado. O pendente precisa dele tanto quanto: é enquanto
            espera que ele tem tempo de completar. */}
        {eu && (
          <section className="mt-6 rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <button onClick={() => setAbrirCadastro((v) => !v)}
              className="flex w-full items-center justify-between text-left">
              <span>
                <span className="font-display text-base font-bold">Meu cadastro</span>
                <span className="ml-2 text-[12px] text-white/45">
                  dados para o repasse dos honorários
                </span>
              </span>
              <span className={`text-xs ${eu.falta_dados_bancarios ? "text-[#E5A44C]" : "text-[#1DB954]"}`}>
                {eu.falta_dados_bancarios ? "falta preencher" : "✓ completo"}
              </span>
            </button>

            {eu.falta_dados_bancarios && !abrirCadastro && (
              <p className="mt-2 text-[13px] leading-relaxed text-white/55">
                Sem a chave PIX ou a conta, o escritório não consegue repassar
                a sua parte — o valor fica parado esperando um dado que leva um
                minuto para informar.
              </p>
            )}

            {abrirCadastro && (
              <div className="mt-4 space-y-3">
                <div className="grid grid-cols-[7rem_1fr] gap-2">
                  <select value={ban.pix_tipo}
                    onChange={(e) => setBan({ ...ban, pix_tipo: e.target.value })}
                    className={campo}>
                    <option value="">Chave PIX</option>
                    <option value="CPF">CPF</option>
                    <option value="CNPJ">CNPJ</option>
                    <option value="EMAIL">E-mail</option>
                    <option value="TELEFONE">Telefone</option>
                    <option value="ALEATORIA">Aleatória</option>
                  </select>
                  <input value={ban.pix_chave} placeholder="a chave"
                    onChange={(e) => setBan({ ...ban, pix_chave: e.target.value })}
                    className={campo} />
                </div>

                <p className="text-[11px] text-white/35">
                  Ou os dados da conta, se preferir receber por transferência:
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <input value={ban.banco_nome} placeholder="Banco"
                    onChange={(e) => setBan({ ...ban, banco_nome: e.target.value })}
                    className={campo} />
                  <input value={ban.agencia} placeholder="Agência"
                    onChange={(e) => setBan({ ...ban, agencia: e.target.value })}
                    className={campo} />
                  <input value={ban.conta} placeholder="Conta"
                    onChange={(e) => setBan({ ...ban, conta: e.target.value })}
                    className={campo} />
                  <select value={ban.conta_tipo}
                    onChange={(e) => setBan({ ...ban, conta_tipo: e.target.value })}
                    className={campo}>
                    <option value="">Tipo</option>
                    <option value="CORRENTE">Corrente</option>
                    <option value="POUPANCA">Poupança</option>
                  </select>
                </div>

                <input value={ban.whatsapp} placeholder="WhatsApp com DDD"
                  inputMode="tel"
                  onChange={(e) => setBan({ ...ban, whatsapp: e.target.value })}
                  className={`${campo} w-full`} />

                {recado && (
                  <p className="rounded-lg bg-white/5 px-3 py-2 text-[12px] text-white/70">
                    {recado}
                  </p>
                )}

                <button onClick={salvarCadastro} disabled={salvando}
                  className="w-full rounded-lg bg-[#C9A84C] px-4 py-3 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e] disabled:opacity-40">
                  {salvando ? "Salvando…" : "Salvar os dados de pagamento"}
                </button>

                <p className="text-[11px] leading-relaxed text-white/35">
                  A conta precisa ser de titularidade do senhor. O escritório não
                  repassa honorário para conta de terceiro.
                </p>
              </div>
            )}
          </section>
        )}

        <p className="mt-10 border-t border-white/10 pt-5 text-[11px] leading-relaxed text-white/30">
          Tudo o que o senhor vê aqui está coberto pelo sigilo profissional.
          O acesso é pessoal e registrado.
        </p>
      </div>
    </main>
  );
}
