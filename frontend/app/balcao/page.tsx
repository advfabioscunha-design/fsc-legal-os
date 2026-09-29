"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* BALCÃO DE CONTRATOS — a porta de entrada do cliente.

   Uma tela, três passos: escolher o serviço, entrar (ou criar conta) e
   aceitar as regras da contratação. Só depois disso o pedido existe e a
   coleta começa, na tela seguinte.

   A conta é exigida antes da coleta de propósito: os dados que serão
   perguntados (CPF, endereço, valores do negócio) não devem ficar num
   formulário anônimo que ninguém sabe de quem é. */

type Tipo = {
  id: string; nome: string; base_legal: string; preco: number;
  documentos: string[]; alerta?: string | null;
};

export default function Balcao() {
  const router = useRouter();
  const [tipos, setTipos] = useState<Tipo[]>([]);
  const [escolhido, setEscolhido] = useState<Tipo | null>(null);
  const [comOrientacao, setComOrientacao] = useState(false);
  const [comTimbre, setComTimbre] = useState(true);

  const [sessao, setSessao] = useState<any>(null);
  const [modo, setModo] = useState<"entrar" | "criar" | "recuperar" | "semEmail">("entrar");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [cpf, setCpf] = useState("");
  const [nascimento, setNascimento] = useState("");
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const [termo, setTermo] = useState<any>(null);
  const [pedidoId, setPedidoId] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/contratos/tipos`).then((r) => r.json())
      .then((d) => setTipos(Array.isArray(d) ? d : [])).catch(() => setTipos([]));
    supabase.auth.getSession().then(({ data }) => setSessao(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSessao(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  const reais = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  async function entrar() {
    setOcupado(true); setErro(""); setAviso("");
    const { error } = await supabase.auth.signInWithPassword({ email, password: senha });
    if (error) setErro("E-mail ou senha não conferem. Se esqueceu a senha, use a opção abaixo.");
    setOcupado(false);
  }

  async function criarConta() {
    setOcupado(true); setErro(""); setAviso("");
    if (nome.trim().length < 5) { setErro("Informe seu nome completo."); setOcupado(false); return; }
    if (senha.length < 8) { setErro("A senha precisa ter pelo menos 8 caracteres."); setOcupado(false); return; }
    const { error } = await supabase.auth.signUp({
      email, password: senha, options: { data: { nome } },
    });
    if (error) {
      setErro(error.message.includes("already")
        ? "Já existe conta com este e-mail. Entre com sua senha ou use “Esqueci a senha”."
        : "Não foi possível criar a conta agora.");
    } else {
      setAviso("Conta criada. Confira seu e-mail para confirmar o cadastro e depois entre.");
      setModo("entrar");
    }
    setOcupado(false);
  }

  async function recuperarSenha() {
    setOcupado(true); setErro(""); setAviso("");
    /* O limite fica no servidor: sem ele, o 'esqueci a senha' vira
       máquina de encher a caixa de entrada de outra pessoa. */
    try {
      const lim = await fetch(`${API}/api/v1/acesso/limite`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (lim.status === 429) {
        const d = await lim.json().catch(() => ({} as any));
        setErro(d.detail || "Muitas tentativas. Aguarde uma hora.");
        setOcupado(false); return;
      }
    } catch { /* contador fora do ar não pode travar quem precisa */ }

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/balcao`,
    });
    // Resposta igual exista ou não a conta: dizer que o e-mail "não
    // está cadastrado" entrega a informação a quem está tentando
    // descobrir quem é cliente do escritório.
    setAviso("Se houver conta com este e-mail, enviamos o link para criar uma "
      + "nova senha. Abra seu e-mail, defina a senha nova e volte aqui para entrar.");
    if (error) console.warn(error.message);
    setOcupado(false);
  }

  async function recuperarSemEmail() {
    setOcupado(true); setErro(""); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/acesso/trocar-email`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cpf, nascimento, novo_email: email }),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) setErro(d.detail || "Não foi possível registrar o pedido.");
      else setAviso(d.mensagem);
    } catch { setErro("Não foi possível falar com o servidor."); }
    setOcupado(false);
  }

  /* Criado o pedido, buscamos o termo de contratação para o cliente
     ler antes de qualquer coleta. */
  async function comecar() {
    if (!escolhido) return;
    setOcupado(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipo: escolhido.id, com_orientacao: comOrientacao, com_timbre: comTimbre,
        }),
      });
      const p = await r.json();
      if (!r.ok) { setErro(p.detail || "Não foi possível abrir o pedido."); return; }
      setPedidoId(p.id);
      const t = await fetch(`${API}/api/v1/contratos/pedidos/${p.id}/termo-contratacao`)
        .then((x) => x.json());
      setTermo(t);
    } catch { setErro("Não foi possível falar com o servidor."); }
    finally { setOcupado(false); }
  }

  async function aceitar() {
    if (!pedidoId) return;
    setOcupado(true);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/termo-contratacao`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aceito: true }),
      });
      if (r.ok) router.push(`/balcao/${pedidoId}`);
      else setErro("Não foi possível registrar o aceite.");
    } finally { setOcupado(false); }
  }

  return (
    <main className="min-h-screen bg-[#0A1628] px-4 py-10 text-white">
      <div className="mx-auto max-w-3xl">
        <header className="mb-8">
          <p className="text-lg font-bold">FC <span className="text-[#C9A24D]">Advocacia</span></p>
          <h1 className="mt-2 text-2xl font-bold">Contratos e documentos</h1>
          <p className="mt-1 text-sm text-white/60">
            Documento elaborado conforme a lei aplicável, revisado por advogado
            e assinado eletronicamente, sem sair de casa.
          </p>
        </header>

        {/* PASSO 3 — termo de contratação */}
        {termo ? (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-6">
            <h2 className="text-sm font-bold text-[#C9A24D]">Antes de começar</h2>
            <pre className="mt-3 max-h-[46vh] overflow-y-auto whitespace-pre-wrap rounded-xl bg-[#0A1628] p-4 text-xs leading-relaxed text-white/80">
              {termo.texto}
            </pre>
            {erro && <p className="mt-3 text-xs text-[#C0392B]">{erro}</p>}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button onClick={aceitar} disabled={ocupado}
                className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
                {ocupado ? "Registrando…" : "Li e aceito"}
              </button>
              <button onClick={() => { setTermo(null); setPedidoId(null); }}
                className="text-sm text-white/50 underline hover:text-white">
                voltar
              </button>
              <span className="ml-auto text-xs text-white/40">
                O aceite fica registrado com data, hora e versão do texto.
              </span>
            </div>
          </section>
        ) : !sessao ? (
          /* PASSO 2 — conta */
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-6">
            <h2 className="text-sm font-bold text-[#C9A24D]">
              {modo === "criar" ? "Criar conta"
                : modo === "recuperar" ? "Esqueci a senha"
                : modo === "semEmail" ? "Não lembro o e-mail cadastrado"
                : "Entrar"}
            </h2>

            <div className="mt-4 grid gap-3">
              {modo === "criar" && (
                <input value={nome} onChange={(e) => setNome(e.target.value)}
                  placeholder="Nome completo"
                  className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm outline-none focus:border-[#C9A84C]" />
              )}
              {modo === "semEmail" && (
                <>
                  <p className="rounded-lg border border-[#E5A44C]/40 bg-[#E5A44C]/10 px-3 py-2 text-[11px] leading-relaxed text-white/75">
                    Como o e-mail cadastrado é o único canal já confirmado, a troca
                    não é automática: vamos ligar no telefone que você cadastrou
                    para confirmar que é você. É o mesmo cuidado que o banco toma.
                  </p>
                  <input value={cpf} onChange={(e) => setCpf(e.target.value)}
                    placeholder="Seu CPF"
                    className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm outline-none focus:border-[#C9A84C]" />
                  <label className="text-xs text-white/50">
                    Data de nascimento
                    <input value={nascimento} onChange={(e) => setNascimento(e.target.value)}
                      type="date"
                      className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm text-white outline-none focus:border-[#C9A84C]" />
                  </label>
                </>
              )}
              <input value={email} onChange={(e) => setEmail(e.target.value)}
                type="email"
                placeholder={modo === "semEmail" ? "E-mail novo, que passará a ser o seu acesso" : "E-mail"}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm outline-none focus:border-[#C9A84C]" />
              {(modo === "entrar" || modo === "criar") && (
                <input value={senha} onChange={(e) => setSenha(e.target.value)}
                  type="password" placeholder="Senha"
                  onKeyDown={(e) => e.key === "Enter" && (modo === "entrar" ? entrar() : criarConta())}
                  className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm outline-none focus:border-[#C9A84C]" />
              )}
            </div>

            {erro && <p className="mt-3 text-xs text-[#C0392B]">{erro}</p>}
            {aviso && <p className="mt-3 rounded-lg bg-[#1DB954]/10 px-3 py-2 text-xs text-[#1DB954]">{aviso}</p>}

            <button
              onClick={modo === "entrar" ? entrar : modo === "criar" ? criarConta
                : modo === "recuperar" ? recuperarSenha : recuperarSemEmail}
              disabled={ocupado}
              className="mt-4 w-full rounded-lg bg-[#C9A84C] py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
              {ocupado ? "Aguarde…"
                : modo === "entrar" ? "Entrar"
                : modo === "criar" ? "Criar conta"
                : modo === "recuperar" ? "Enviar link para criar nova senha"
                : "Enviar pedido"}
            </button>

            <div className="mt-4 flex flex-wrap gap-4 text-xs text-white/45">
              {modo !== "entrar" && (
                <button onClick={() => { setModo("entrar"); setErro(""); setAviso(""); }}
                  className="underline hover:text-white">já tenho conta</button>
              )}
              {modo !== "criar" && (
                <button onClick={() => { setModo("criar"); setErro(""); setAviso(""); }}
                  className="underline hover:text-white">criar conta</button>
              )}
              {modo !== "recuperar" && (
                <button onClick={() => { setModo("recuperar"); setErro(""); setAviso(""); }}
                  className="underline hover:text-white">esqueci a senha</button>
              )}
              {modo !== "semEmail" && (
                <button onClick={() => { setModo("semEmail"); setErro(""); setAviso(""); }}
                  className="underline hover:text-white">não lembro o e-mail</button>
              )}
            </div>
          </section>
        ) : (
          /* PASSO 1 — escolher o serviço */
          <section>
            <div className="mb-4 flex items-center justify-between text-xs text-white/50">
              <span>Escolha o documento que você precisa</span>
              <button onClick={() => supabase.auth.signOut()} className="underline hover:text-white">sair</button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {tipos.map((t) => (
                <button key={t.id} onClick={() => setEscolhido(t)}
                  className={`rounded-xl border p-4 text-left transition ${
                    escolhido?.id === t.id
                      ? "border-[#C9A84C] bg-[#C9A84C]/10"
                      : "border-white/10 bg-[#0B1F3B] hover:border-white/25"}`}>
                  <p className="text-sm font-bold text-white/90">{t.nome}</p>
                  <p className="mt-0.5 text-[11px] text-white/45">{t.base_legal}</p>
                  <p className="mt-2 text-sm font-bold text-[#C9A24D]">{reais(t.preco)}</p>
                </button>
              ))}
            </div>

            {escolhido && (
              <div className="mt-5 rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
                <h3 className="text-sm font-bold text-white/90">{escolhido.nome}</h3>

                {escolhido.alerta && (
                  <div className="mt-3 rounded-xl border border-[#E5A44C]/40 bg-[#E5A44C]/10 p-3">
                    <p className="text-xs font-bold text-[#E5A44C]">Importante, leia antes de contratar</p>
                    <p className="mt-1 text-xs leading-relaxed text-white/75">{escolhido.alerta}</p>
                  </div>
                )}

                <p className="mt-4 text-xs font-semibold text-white/60">
                  Documentos que ajudam (você pode digitar as informações ou enviar cópia):
                </p>
                <ul className="mt-1 space-y-0.5">
                  {escolhido.documentos.map((d, i) => (
                    <li key={i} className="text-xs text-white/50">• {d}</li>
                  ))}
                </ul>

                <div className="mt-4 space-y-2">
                  <label className="flex cursor-pointer items-start gap-2 text-xs text-white/70">
                    <input type="checkbox" checked={comOrientacao}
                      onChange={(e) => setComOrientacao(e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-[#C9A84C]" />
                    <span>
                      Quero <b>orientação jurídica antes</b> (+ R$ 250,00) — atendimento por
                      vídeo com um advogado, agendado por aqui, antes da elaboração.
                    </span>
                  </label>
                  <label className="flex cursor-pointer items-start gap-2 text-xs text-white/70">
                    <input type="checkbox" checked={!comTimbre}
                      onChange={(e) => setComTimbre(!e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-[#C9A84C]" />
                    <span>Prefiro o documento em folha branca, sem o timbre do escritório.</span>
                  </label>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <span className="text-lg font-bold text-[#C9A24D]">
                    {reais(escolhido.preco + (comOrientacao ? 250 : 0))}
                  </span>
                  <button onClick={comecar} disabled={ocupado}
                    className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
                    {ocupado ? "Abrindo…" : "Continuar"}
                  </button>
                  {erro && <span className="text-xs text-[#C0392B]">{erro}</span>}
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
