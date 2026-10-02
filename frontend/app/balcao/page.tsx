"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabaseClient";
import { useRascunho } from "@/lib/rascunho";
import BotaoGoogle from "../components/BotaoGoogle";
import { faltaNoCadastro } from "@/lib/cadastro";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* BALCÃO DE CONTRATOS, a porta de entrada do cliente.

   Uma tela, três passos: escolher o serviço, entrar (ou criar conta) e
   aceitar as regras da contratação. Só depois disso o pedido existe e a
   coleta começa, na tela seguinte.

   A conta é exigida antes da coleta de propósito: os dados que serão
   perguntados (CPF, endereço, valores do negócio) não devem ficar num
   formulário anônimo que ninguém sabe de quem é. */

type Tipo = {
  id: string; nome: string; base_legal: string;
  documentos: string[]; alerta?: string | null;
};

export default function Balcao() {
  const router = useRouter();
  const [tipos, setTipos] = useState<Tipo[]>([]);
  const [escolhido, setEscolhido] = useState<Tipo | null>(null);
  const [comOrientacao, setComOrientacao] = useState(false);
  const [busca, setBusca] = useState("");
  const [livre, setLivre] = useState(false);
  const [descricaoLivre, setDescricaoLivre] = useState("");

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
  /* O pedido que esta pessoa já tem esperando informação. Null é
     "ainda não perguntei"; undefined seria ambíguo demais para uma
     decisão que decide o que a tela inteira mostra. */
  const [emAberto, setEmAberto] = useState<any | null>(null);
  const [conferindo, setConferindo] = useState(true);
  /* A conta deixou de ser etapa: ela é a porta, e quem não entrou não
     chega aqui. Restam três: escolher o documento, negociar e ler o
     termo. "fechado" é o instante entre o sim e o termo, em que o
     pedido é amarrado ao cadastro. */
  const [etapa, setEtapa] = useState<"tipo" | "negociar" | "fechado" | "termo">("tipo");
  const [combinado, setCombinado] = useState<any>(null);

  // Fechado o preço, amarra o pedido ao cadastro e busca o termo. O
  // vínculo vem do token, e não de um cliente_id que a tela mandaria:
  // era isso que fazia todo pedido nascer órfão.
  useEffect(() => {
    if (etapa !== "fechado" || !sessao || !pedidoId) return;
    (async () => {
      try {
        await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/vincular`, {
          method: "POST",
          headers: { Authorization: `Bearer ${sessao.access_token}` },
        });
        const t = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/termo-contratacao`)
          .then((x) => x.json());
        setTermo(t); setEtapa("termo");
      } catch { setErro("Não consegui continuar. Tente de novo."); }
    })();
  }, [etapa, sessao, pedidoId]);

  useEffect(() => {
    fetch(`${API}/api/v1/contratos/tipos`).then((r) => r.json())
      .then((d) => setTipos(Array.isArray(d) ? d : [])).catch(() => setTipos([]));
    // Quem chega pelo "Pedir meu contrato" ainda não tem conta. Abrir
    // em "Entrar" faria essa pessoa procurar o link de cadastro antes
    // de conseguir começar.
    if (new URLSearchParams(window.location.search).get("novo") === "1") {
      setModo("criar");
    }
    supabase.auth.getSession().then(({ data }) => setSessao(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSessao(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  /* UM PEDIDO DE CADA VEZ, ENQUANTO O PRIMEIRO ESPERA INFORMAÇÃO

     Quem clicava duas vezes em "Pedir meu contrato" abria um segundo
     cadastro em branco, e acabava com dois protocolos para o mesmo
     documento: um com metade dos dados, outro vazio. Do lado do
     escritório viram dois pedidos, e alguém tem de descobrir qual
     vale.

     Enquanto houver pedido esperando pagamento ou esperando as
     informações, o balcão não abre a lista de novo: leva direto para
     aquele, de onde a pessoa parou. Passada essa fase, a lista volta
     a abrir normalmente, porque pedir um segundo documento é
     legítimo e comum. */
  useEffect(() => {
    if (!sessao) { setConferindo(false); return; }
    let vivo = true;
    (async () => {
      setConferindo(true);
      try {
        const r = await fetch(`${API}/api/v1/contratos/meus-pedidos`, {
          headers: { Authorization: `Bearer ${sessao.access_token}` },
        });
        const lista = await r.json();
        const esperando = (Array.isArray(lista) ? lista : [])
          .find((p: any) => ["PAGAMENTO", "COLETA"].includes(p.fase));
        if (vivo) setEmAberto(esperando || null);
      } catch { /* sem isto a tela segue como antes, e não como travada */ }
      finally { if (vivo) setConferindo(false); }
    })();
    return () => { vivo = false; };
  }, [sessao]);

  /* CONCLUIR O CADASTRO ANTES DE PEDIR O DOCUMENTO

     Quem entra aqui — com senha ou com o Google — pode estar com o
     cadastro pela metade: sem nome completo, sem WhatsApp, sem o aceite
     dos termos. Nada disso pode faltar na hora de emitir um contrato, e
     perguntar depois, no meio da coleta, é interromper a pessoa quando
     ela já está adiantada.

     A tela de conclusão decide sozinha se tem o que perguntar. Quem já
     respondeu volta para cá sem ver nada, e é por isso que esta
     verificação pode ser simples assim. */
  useEffect(() => {
    if (!sessao) return;
    let vivo = true;
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/cliente/cadastro`, {
          headers: { Authorization: `Bearer ${sessao.access_token}` },
        });
        const c = await r.json().catch(() => ({} as any));
        if (!vivo) return;
        if (faltaNoCadastro(c)) router.push("/entrada/completar?next=%2Fbalcao");
      } catch { /* consulta que falhou não pode fechar a porta do balcão */ }
    })();
    return () => { vivo = false; };
  }, [sessao, router]);

  const reais = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  /* A busca casa com nome e base legal, sem acento e sem caixa: quem
     digita "locacao" tem de achar "Locação", e quem digita
     "inquilinato" tem de achar a locação de imóvel, porque muita gente
     procura pela lei e não pelo nome do documento. */
  const sem = (t: string) =>
    t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const achados = busca.trim()
    ? tipos.filter((t) => sem(`${t.nome} ${t.base_legal}`).includes(sem(busca.trim())))
    : tipos;

  async function entrar() {
    setOcupado(true); setErro(""); setAviso("");
    const { error } = await supabase.auth.signInWithPassword({ email, password: senha });
    if (error) setErro("E-mail ou senha não conferem. Se esqueceu a senha, use a opção abaixo.");
    setOcupado(false);
  }

  async function criarConta() {
    setOcupado(true); setErro(""); setAviso("");
    if (nome.trim().length < 5) { setErro("Informe seu nome completo."); setOcupado(false); return; }
    if (senha.length < 6) { setErro("A senha precisa ter pelo menos 6 caracteres."); setOcupado(false); return; }
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
      redirectTo: `${window.location.origin}/nova-senha`,
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
    const descrito = descricaoLivre.trim();
    if (!escolhido && descrito.length < 8) return;
    /* CLIQUE DUPLO NÃO NASCE PEDIDO DUPLO

       `ocupado` já desabilita o botão, mas o clique repetido chega
       antes do React redesenhar, e nessa fresta cabiam dois POST. Dois
       POST são dois protocolos, e alguém no escritório vai ter de
       descobrir qual dos dois vale. A guarda é aqui, no início da
       função, que é o único ponto por onde os dois passam. */
    if (ocupado || pedidoId) return;
    setOcupado(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          escolhido
            ? { tipo: escolhido.id, com_orientacao: comOrientacao }
            // Sem tipo na lista, o pedido nasce OUTRO e carrega a
            // descrição do cliente. O timbre não é perguntado aqui:
            // vem depois do pagamento, com o resto da coleta.
            : { tipo: "OUTRO", com_orientacao: false, servico_livre: descrito }),
      });
      const p = await r.json();
      if (!r.ok) { setErro(p.detail || "Não foi possível abrir o pedido."); return; }
      setPedidoId(p.id);
      // A proposta vem ANTES do cadastro. Pedir CPF e endereço de quem
      // ainda não decidiu contratar é o jeito mais rápido de perder a
      // pessoa, e são dados que não deveríamos ter guardado.
      setEtapa("negociar");
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
            Documento elaborado conforme a lei aplicável, revisado antes da
            entrega e assinado eletronicamente, sem sair de casa.
          </p>
        </header>

        {/* A CONTA VEM PRIMEIRO

            Antes o cadastro ficava depois da negociação, para não pedir
            dados a quem ainda não tinha decidido. A ordem mudou por
            escolha do escritório: quem pede um contrato passa a criar o
            acesso na entrada, e assim, ao sair e voltar, entra com a
            senha e reencontra o pedido onde parou, junto com os
            processos e os outros serviços dele.

            O que se ganha: nenhum pedido órfão, e um só lugar para
            acompanhar tudo. O que se perde: parte de quem só estava
            olhando desiste ao ver um formulário. É reversível, se um
            dia o número mostrar que não valeu. */}
        {!sessao ? (
          <Entrada
            modo={modo} setModo={setModo}
            nome={nome} setNome={setNome}
            email={email} setEmail={setEmail}
            senha={senha} setSenha={setSenha}
            cpf={cpf} setCpf={setCpf}
            nascimento={nascimento} setNascimento={setNascimento}
            erro={erro} aviso={aviso} ocupado={ocupado}
            entrar={entrar} criarConta={criarConta}
            recuperarSenha={recuperarSenha} recuperarSemEmail={recuperarSemEmail}
          />
        ) : conferindo ? (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-6 text-sm text-white/50">
            Um instante, conferindo os seus pedidos…
          </section>
        ) : emAberto && etapa === "tipo" ? (
          /* JÁ EXISTE UM PEDIDO ESPERANDO INFORMAÇÃO

             Aqui a lista não abre. Abrir seria convidar a pessoa a
             começar de novo o que ela já começou, e o resultado é dois
             protocolos para o mesmo documento. */
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-6">
            <span className="inline-flex items-center gap-2 rounded-full bg-[#C9A84C]/15 px-3 py-1 text-[11px] font-bold text-[#C9A84C]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#C9A84C]" />
              Pedido em andamento
            </span>
            <h2 className="mt-3 text-lg font-bold text-white">
              Você já tem um pedido aberto
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-white/60">
              É o protocolo <b className="font-mono text-white/85">{emAberto.numero}</b>,
              {" "}
              {String(emAberto.tipo) === "OUTRO" && emAberto.servico_livre
                ? emAberto.servico_livre
                : String(emAberto.tipo || "").replaceAll("_", " ").toLowerCase()}
              . Ele está {emAberto.fase === "PAGAMENTO"
                ? "esperando a confirmação do pagamento"
                : "esperando as informações do documento"}.
            </p>
            <p className="mt-2 text-xs leading-relaxed text-white/45">
              Continue de onde parou. Tudo o que você já informou está
              guardado, e não é preciso preencher nada de novo.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button onClick={() => router.push(`/balcao/${emAberto.id}`)}
                className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e]">
                Continuar o meu pedido
              </button>
              <a href="/cliente"
                className="text-sm text-white/50 underline hover:text-white">
                ver todos os meus pedidos
              </a>
            </div>
          </section>
        ) : etapa === "negociar" && pedidoId ? (
          <Negociacao pedidoId={pedidoId} escolhido={escolhido}
            aoFechar={(c) => { setCombinado(c); setEtapa("fechado"); }}
            aoVoltar={() => { setEtapa("tipo"); setPedidoId(null); }} />
        ) : etapa === "termo" && termo ? (
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
        ) : (
          /* PASSO 1, escolher o serviço */
          <section>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 text-xs text-white/50">
              <span>Escolha o documento que você precisa</span>
              <span className="flex items-center gap-4">
                {/* A conta do balcão é a mesma da área do cliente. Sem
                    este caminho, quem entrou por aqui não descobriria
                    que tem uma área inteira do outro lado. */}
                <a href="/cliente" className="underline hover:text-white">
                  meus pedidos e processos
                </a>
                <button onClick={() => supabase.auth.signOut()} className="underline hover:text-white">sair</button>
              </span>
            </div>

            {/* A BUSCA, E O QUE FAZER QUANDO ELA NÃO ACHA NADA

                A lista tem dez tipos e o mundo tem mais do que dez
                documentos. Quem procurava "acordo de namoro" ou
                "cessão de cota" batia numa parede: nenhum campo para
                dizer o que queria, e ia embora sem o escritório nem
                ficar sabendo o que ela procurava.

                A busca lê nome e base legal, porque muita gente procura
                pela lei ("inquilinato") e não pelo nome do documento. */}
            <div className="relative mb-4">
              <svg className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35"
                fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path strokeLinecap="round" d="m20 20-3.5-3.5" />
              </svg>
              <input value={busca} onChange={(e) => setBusca(e.target.value)}
                placeholder="Procure pelo nome do documento, por exemplo aluguel, dívida, rescisão"
                className="w-full rounded-lg border border-white/15 bg-[#0B1F3B] py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/35 outline-none focus:border-[#C9A84C]" />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {achados.map((t) => (
                <button key={t.id} onClick={() => { setEscolhido(t); setLivre(false); }}
                  className={`rounded-xl border p-4 text-left transition ${
                    escolhido?.id === t.id && !livre
                      ? "border-[#C9A84C] bg-[#C9A84C]/10"
                      : "border-white/10 bg-[#0B1F3B] hover:border-white/25"}`}>
                  <p className="text-sm font-bold text-white/90">{t.nome}</p>
                  <p className="mt-0.5 text-[11px] text-white/45">{t.base_legal}</p>
                </button>
              ))}
            </div>

            {/* Não achou. A porta continua aberta. */}
            <div className={`mt-4 rounded-xl border p-4 transition ${
              livre ? "border-[#C9A84C] bg-[#C9A84C]/10" : "border-dashed border-white/20 bg-[#0B1F3B]/60"}`}>
              {achados.length === 0 && busca.trim() && (
                <p className="mb-2 text-xs text-white/60">
                  Nenhum documento da lista corresponde a <b>{busca.trim()}</b>.
                </p>
              )}
              <p className="text-sm font-bold text-white/90">
                Não encontrou o que precisa?
              </p>
              <p className="mt-1 text-xs text-white/55">
                Descreva com as suas palavras. O escritório lê antes de
                confirmar prazo e condições, e o atendimento segue normalmente.
              </p>
              <textarea
                value={descricaoLivre}
                onChange={(e) => { setDescricaoLivre(e.target.value); setLivre(true); setEscolhido(null); }}
                rows={3}
                placeholder="Por exemplo: um acordo entre dois sócios para dividir os lucros de uma loja que temos juntos"
                className="mt-3 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm text-white placeholder:text-white/30 outline-none focus:border-[#C9A84C]" />
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button onClick={comecar}
                  disabled={ocupado || descricaoLivre.trim().length < 8}
                  className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-40">
                  {ocupado ? "Abrindo…" : "Continuar o atendimento"}
                </button>
                <span className="text-[11px] text-white/35">
                  Mínimo de uma frase, para o escritório entender o pedido.
                </span>
              </div>
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
                      Quero <b>orientação jurídica antes</b>: atendimento por vídeo com
                      o escritório, agendado por aqui, antes da elaboração. Esse
                      atendimento é contratado à parte.
                    </span>
                  </label>
                  {/* A escolha entre papel timbrado e folha branca saiu
                      daqui. Nesta tela a pessoa ainda não sabe quanto
                      custa nem se vai contratar, e a pergunta não
                      significa nada. Ela aparece depois do pagamento,
                      junto com o resto da coleta, quando o escritório já
                      está montando o documento dela. */}
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  {/* O valor NÃO aparece aqui.

                      Preço em cima da escolha transforma a página em
                      prateleira de loja, e advocacia não é isso: o
                      Provimento 205/2021 da OAB não admite anúncio de
                      honorário ao público. Além disso, número antes de
                      contexto faz a pessoa comparar o que ainda não
                      entendeu. O valor é dito no atendimento, a quem já
                      escolheu o documento, com a explicação do que está
                      incluído. */}
                  <button onClick={comecar} disabled={ocupado}
                    className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
                    {ocupado ? "Abrindo…" : "Falar sobre este documento"}
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


/* ── A proposta e a conversa sobre ela ─────────────────────────────

   O escritório dá valor ao serviço antes de falar de preço, escuta a
   objeção antes de descontar, e tem dois degraus de desconto, 10% na
   resistência, 20% quando a pessoa sinaliza que vai embora.

   Quem calcula o preço é o servidor, não o modelo: um modelo instruído
   a negociar, se lhe derem a calculadora, acaba concedendo mais do que
   devia para agradar quem insiste.

   A saída da página é detectada aqui, no navegador, e mandada como um
   sinal, não se pede a uma IA que adivinhe intenção de saída. */
function Negociacao({ pedidoId, escolhido, aoFechar, aoVoltar }: {
  pedidoId: string;
  escolhido: Tipo | null;
  aoFechar: (conta: any) => void;
  aoVoltar: () => void;
}) {
  const [falas, setFalas] = useState<{ de: "agente" | "cliente"; texto: string }[]>([]);
  const [conta, setConta] = useState<any>(null);
  const [texto, setTexto, limparRascunho] = useRascunho(`negociacao-${pedidoId}`);
  const [pensando, setPensando] = useState(false);
  const [usouSaida, setUsouSaida] = useState(false);
  const [propostaEnviada, setPropostaEnviada] = useState(false);
  const [enviandoArquivo, setEnviandoArquivo] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);
  const camera = useRef<HTMLInputElement>(null);
  const anexo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      setPensando(true);
      try {
        const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/negociar/abrir`,
          { method: "POST" });
        const d = await r.json();
        if (d?.texto) setFalas([{ de: "agente", texto: d.texto }]);
        // A abertura não traz valor de propósito. O painel de preço só
        // acende quando o primeiro número sai, lá adiante.
        if (d?.conta) setConta(d.conta);
      } finally { setPensando(false); }
    })();
  }, [pedidoId]);

  /* Quem rola é a caixa da conversa, pelo próprio scrollTop.
     `scrollIntoView` rola todos os ancestrais, e com isso arrasta a
     página inteira, o que atrapalha quem está lendo outra parte. */
  useEffect(() => {
    const c = caixa.current;
    if (c) c.scrollTop = c.scrollHeight;
  }, [falas]);

  const enviar = useCallback(async (msg: string, vaiSair = false) => {
    if (!msg.trim() && !vaiSair) return;
    if (msg.trim()) setFalas((f) => [...f, { de: "cliente", texto: msg }]);
    limparRascunho(); setPensando(true);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/negociar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensagem: msg || "(fechando a página)", vai_sair: vaiSair }),
      });
      const d = await r.json();
      if (d?.texto) setFalas((f) => [...f, { de: "agente", texto: d.texto }]);
      if (d?.conta) setConta(d.conta);
      if (d?.proposta_registrada) setPropostaEnviada(true);
      if (d?.fechou) aoFechar(d.conta);
    } catch {
      // O texto volta para a caixa: quem perdeu a conexão não pode
      // perder também o que escreveu.
      if (msg.trim()) setTexto(msg);
      setFalas((f) => [...f, { de: "agente", texto: "Tive um problema de conexão. Pode repetir?" }]);
    } finally { setPensando(false); }
  }, [pedidoId, aoFechar]);

  /* O arquivo sobe pela mesma porta dos documentos do pedido, e a
     conversa recebe uma linha dizendo o que chegou. Anexo mudo é
     arquivo que ninguém sabe por que está ali. */
  const anexarNaConversa = useCallback(
    async (lista: FileList | null, origem: "FOTO" | "ARQUIVO") => {
      if (!lista || lista.length === 0) return;
      setEnviandoArquivo(true);
      try {
        const fd = new FormData();
        Array.from(lista).forEach((f) => fd.append("arquivos", f));
        const r = await fetch(
          `${API}/api/v1/contratos/pedidos/${pedidoId}/documentos?rotulo=${encodeURIComponent("Enviado na conversa")}`,
          { method: "POST", body: fd });
        if (!r.ok) {
          setFalas((f) => [...f, { de: "agente",
            texto: "Não consegui receber o arquivo. Pode tentar de novo?" }]);
          return;
        }
        const nomes = Array.from(lista).map((f) => f.name).join(", ");
        await enviar(origem === "FOTO"
          ? `Mandei ${lista.length === 1 ? "uma foto" : `${lista.length} fotos`}: ${nomes}`
          : `Mandei ${lista.length === 1 ? "um arquivo" : `${lista.length} arquivos`}: ${nomes}`);
      } catch {
        setFalas((f) => [...f, { de: "agente",
          texto: "Tive um problema para receber o arquivo. Pode tentar de novo?" }]);
      } finally {
        setEnviandoArquivo(false);
        if (camera.current) camera.current.value = "";
        if (anexo.current) anexo.current.value = "";
      }
    }, [pedidoId, enviar]);

  // Intenção de saída: o mouse indo para fora da janela pela borda de
  // cima é o gesto de quem vai fechar a aba. Uma vez só por sessão ,
  // repetir a última proposta a cada movimento de mouse é perseguição,
  // não venda.
  useEffect(() => {
    if (usouSaida) return;
    const sair = (e: MouseEvent) => {
      if (e.clientY > 0) return;
      setUsouSaida(true);
      enviar("", true);
    };
    document.addEventListener("mouseleave", sair);
    return () => document.removeEventListener("mouseleave", sair);
  }, [usouSaida, enviar]);

  const reais = (v: number) =>
    Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-[#C9A24D]">{escolhido?.nome}</h2>
          <p className="text-[11px] text-white/45">{escolhido?.base_legal}</p>
        </div>
        {/* O PAINEL DE VALOR ACENDE DEPOIS

            Ele nascia junto com a conversa e mostrava o preço antes de
            a pessoa ter lido uma linha sobre o que está comprando.
            Número sozinho no alto da tela empurra a comparação com
            modelo de internet, que é a única régua que o cliente tem
            quando ninguém lhe deu outra.

            Agora ele só aparece quando o primeiro valor é apresentado
            na conversa, e a cada desconto o valor anterior fica ao
            lado, riscado. Ver o número descer vale mais do que ler
            "com 20% de desconto". */}
        {conta && (
          <div className="text-right">
            <div className="flex items-baseline justify-end gap-2">
              {conta.desconto_pct > 0 && conta.total_sem_desconto
                && Number(conta.total_sem_desconto) > Number(conta.total) && (
                <span className="text-xs text-white/35 line-through">
                  {reais(Number(conta.total_sem_desconto))}
                </span>
              )}
              <p className="text-lg font-bold text-white">{reais(conta.total)}</p>
            </div>
            {conta.desconto_pct > 0 && (
              <p className="text-[10px] text-[#1DB954]">
                {conta.desconto_pct}% de desconto aplicado
              </p>
            )}
            <p className="text-[10px] text-white/40">entrega em até {conta.horas}h</p>
          </div>
        )}
      </div>

      <div ref={caixa}
        className="max-h-[42vh] space-y-2 overflow-y-auto rounded-xl bg-[#0A1628] p-3">
        {falas.map((f, i) => (
          <div key={i}
            className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${f.de === "agente"
              ? "bg-white/5 text-white/85"
              : "ml-auto bg-[#C9A84C]/15 text-white/90"}`}>
            <p className="whitespace-pre-line">{f.texto}</p>
          </div>
        ))}
        {pensando && <p className="text-[11px] text-white/35">digitando…</p>}
      </div>

      {propostaEnviada && (
        <div className="mt-3 rounded-xl border border-[#1DB954]/40 bg-[#1DB954]/10 p-3">
          <p className="text-xs font-bold text-[#1DB954]">
            Sua proposta foi registrada
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-white/70">
            O escritório vai analisar e responder pelo seu e-mail
            em até um dia útil. Você não precisa fazer mais nada agora.
          </p>
        </div>
      )}

      <div className="mt-3 flex gap-2">
        {/* Caixa de várias linhas, e o Enter pula linha: quem está
            negociando escreve frase longa, e no celular a tecla de
            quebrar linha é a mesma de enviar. Quem envia é o botão. */}
        <textarea value={texto} onChange={(e) => setTexto(e.target.value)}
          rows={2}
          placeholder="pergunte, ou diga o que achou do valor"
          className="flex-1 resize-none rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm outline-none focus:border-[#C9A84C]" />
        <button onClick={() => enviar(texto)} disabled={pensando}
          className="rounded-lg border border-white/20 px-4 text-sm text-white/70 hover:border-white/40 disabled:opacity-40">
          Enviar
        </button>
      </div>

      {/* FOTO E ANEXO JÁ AQUI

          Muita gente chega com o contrato antigo, a matrícula ou o
          boleto na mão e quer mostrar antes de decidir. Mandar agora
          poupa a pergunta depois, e o arquivo já nasce amarrado ao
          pedido, que existe desde que a conversa começou. */}
      <input ref={camera} type="file" accept="image/*" capture="environment"
        multiple className="hidden"
        onChange={(e) => anexarNaConversa(e.target.files, "FOTO")} />
      <input ref={anexo} type="file" accept="image/*,application/pdf"
        multiple className="hidden"
        onChange={(e) => anexarNaConversa(e.target.files, "ARQUIVO")} />

      <div className="mt-2 flex flex-wrap gap-2">
        <button type="button" onClick={() => camera.current?.click()}
          disabled={enviandoArquivo}
          className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-1.5 text-[11px] text-white/70 transition hover:border-white/45 disabled:opacity-40">
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none"
            stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M3 8.5A1.5 1.5 0 014.5 7h2L8 5h8l1.5 2h2A1.5 1.5 0 0121 8.5v9A1.5 1.5 0 0119.5 19h-15A1.5 1.5 0 013 17.5v-9z" />
            <circle cx="12" cy="13" r="3.2" />
          </svg>
          Tirar foto
        </button>
        <button type="button" onClick={() => anexo.current?.click()}
          disabled={enviandoArquivo}
          className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-1.5 text-[11px] text-white/70 transition hover:border-white/45 disabled:opacity-40">
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none"
            stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M20 11.5l-7.8 7.8a4.5 4.5 0 01-6.4-6.4l8.1-8.1a3 3 0 014.2 4.2l-8.1 8.1a1.5 1.5 0 01-2.1-2.1l7.4-7.4" />
          </svg>
          Anexar documento
        </button>
        {enviandoArquivo && (
          <span className="self-center text-[10px] text-white/40">enviando…</span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button onClick={() => enviar("Quero contratar por esse valor.")}
          disabled={pensando}
          className="rounded-lg bg-[#1DB954] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#17a349] disabled:opacity-50">
          Quero contratar
        </button>
        <button onClick={() => enviar("Preciso para hoje, em poucas horas. Dá?")}
          disabled={pensando}
          className="rounded-lg border border-white/20 px-4 py-2.5 text-xs text-white/70 hover:border-white/40">
          Preciso com urgência
        </button>
        <button onClick={aoVoltar}
          className="ml-auto text-xs text-white/40 underline hover:text-white">
          escolher outro documento
        </button>
      </div>

      {escolhido?.alerta && (
        <div className="mt-4 rounded-xl border border-[#E5A44C]/40 bg-[#E5A44C]/10 p-3">
          <p className="text-[11px] font-bold text-[#E5A44C]">Importante, leia antes de contratar</p>
          <p className="mt-1 text-[11px] leading-relaxed text-white/75">{escolhido.alerta}</p>
        </div>
      )}
    </section>
  );
}


/* ── A PORTA DE ENTRADA ────────────────────────────────────────
 *
 * Quem chega ao balcão cria o acesso antes de escolher o documento.
 * Duas razões práticas, e nenhuma delas é burocracia:
 *
 * O pedido não fica órfão. Antes, quem fechasse a aba no meio da
 * negociação deixava para trás um pedido sem dono, que ninguém
 * conseguia retomar, nem ele nem o escritório.
 *
 * E há um lugar para voltar. Com a conta criada, sair e retornar é
 * entrar com a senha e reencontrar o serviço onde parou, ao lado dos
 * outros pedidos e dos processos, se houver.
 *
 * O formulário diz isso com todas as letras. Pedir dados sem explicar
 * para quê é o que faz a pessoa fechar a página.
 */
function Entrada({
  modo, setModo, nome, setNome, email, setEmail, senha, setSenha,
  cpf, setCpf, nascimento, setNascimento, erro, aviso, ocupado,
  entrar, criarConta, recuperarSenha, recuperarSemEmail,
}: any) {
  const campo = "rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 text-sm outline-none focus:border-[#C9A84C]";

  return (
    <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-6">
      <h2 className="font-display text-lg font-bold text-white">
        {modo === "criar" ? "Criar seu acesso"
          : modo === "recuperar" ? "Esqueci a senha"
          : modo === "semEmail" ? "Não lembro o e-mail cadastrado"
          : "Entrar"}
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-white/60">
        {modo === "criar"
          ? "É com esse acesso que você acompanha o documento sendo feito, "
            + "conversa com o escritório e volta depois, de onde parou."
          : modo === "entrar"
          ? "Entre para pedir um documento novo ou acompanhar os que você já "
            + "pediu."
          : "Vamos recuperar o seu acesso."}
      </p>

      {/* ENTRAR COM O GOOGLE, NO MEIO DE UM PEDIDO

          Este é o lugar onde a conta mais atrapalha: a pessoa veio
          pedir um contrato e esbarra num cadastro. Um clique resolve —
          e a volta cai aqui mesmo, no balcão, para ela continuar o
          pedido de onde parou, e não na lista de casos.

          Depois do Google ela ainda responde duas perguntas (nome
          completo e WhatsApp), porque o Google não manda telefone e o
          contrato precisa do nome inteiro. Duas, e não um formulário. */}
      {(modo === "entrar" || modo === "criar") && (
        <div className="mt-5">
          <BotaoGoogle destino="/balcao" tom="escuro" />
          <div className="mt-4 flex items-center gap-3">
            <span className="h-px flex-1 bg-white/10" />
            <span className="text-[10px] uppercase tracking-wider text-white/35">
              ou com e-mail e senha
            </span>
            <span className="h-px flex-1 bg-white/10" />
          </div>
        </div>
      )}

      {/* O QUE A CONTA DÁ, ALÉM DE GUARDAR O PEDIDO

          Quem chega aqui está pedindo um documento e não sabe que a
          mesma conta abre a área inteira do cliente. Dizer isso na
          hora do cadastro transforma um formulário chato em algo que
          a pessoa entende por que está preenchendo. */}
      {modo === "criar" && (
        <ul className="mt-4 space-y-2 rounded-xl border border-white/10 bg-black/20 p-4">
          {[
            "Seu pedido fica guardado: sair no meio e voltar é continuar, não recomeçar",
            "Conversa com o escritório registrada, disponível a qualquer hora",
            "Quantos documentos quiser, cada um com o seu número de protocolo",
            "E, se um dia tiver um processo conosco, ele aparece na mesma área",
          ].map((t) => (
            <li key={t} className="flex gap-2.5 text-xs leading-relaxed text-white/70">
              <span aria-hidden="true" className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[#2D7DD2]" />
              {t}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5 grid gap-3">
        {modo === "criar" && (
          <input value={nome} onChange={(e) => setNome(e.target.value)}
            placeholder="Nome completo" className={campo} />
        )}
        {modo === "semEmail" && (
          <>
            <p className="rounded-lg border border-[#E5A44C]/40 bg-[#E5A44C]/10 px-3 py-2 text-[11px] leading-relaxed text-white/75">
              Como o e-mail cadastrado é o único canal já confirmado, a troca
              não é automática: vamos ligar no telefone que você cadastrou
              para confirmar que é você. É o mesmo cuidado que o banco toma.
            </p>
            <input value={cpf} onChange={(e) => setCpf(e.target.value)}
              placeholder="Seu CPF" className={campo} />
            <label className="text-xs text-white/50">
              Data de nascimento
              <input value={nascimento} onChange={(e) => setNascimento(e.target.value)}
                type="date" className={`mt-1 w-full text-white ${campo}`} />
            </label>
          </>
        )}
        <input value={email} onChange={(e) => setEmail(e.target.value)}
          type="email"
          placeholder={modo === "semEmail" ? "E-mail novo, que passará a ser o seu acesso" : "E-mail"}
          className={campo} />
        {(modo === "entrar" || modo === "criar") && (
          <input value={senha} onChange={(e) => setSenha(e.target.value)}
            type="password"
            placeholder={modo === "criar" ? "Senha, pelo menos 6 caracteres" : "Senha"}
            onKeyDown={(e) => e.key === "Enter" && (modo === "entrar" ? entrar() : criarConta())}
            className={campo} />
        )}
      </div>

      {erro && <p className="mt-3 text-xs text-[#C0392B]">{erro}</p>}
      {aviso && <p className="mt-3 rounded-lg bg-[#1DB954]/10 px-3 py-2 text-xs text-[#1DB954]">{aviso}</p>}

      <button
        onClick={modo === "entrar" ? entrar : modo === "criar" ? criarConta
          : modo === "recuperar" ? recuperarSenha : recuperarSemEmail}
        disabled={ocupado}
        className="mt-5 w-full rounded-lg bg-[#C9A84C] py-3 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
        {ocupado ? "Aguarde…"
          : modo === "entrar" ? "Entrar"
          : modo === "criar" ? "Criar acesso e continuar"
          : modo === "recuperar" ? "Enviar link para criar nova senha"
          : "Enviar pedido"}
      </button>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-white/45">
        {modo !== "entrar" && (
          <button onClick={() => setModo("entrar")} className="underline hover:text-white">já tenho acesso</button>
        )}
        {modo !== "criar" && (
          <button onClick={() => setModo("criar")} className="underline hover:text-white">criar acesso</button>
        )}
        {modo !== "recuperar" && (
          <button onClick={() => setModo("recuperar")} className="underline hover:text-white">esqueci a senha</button>
        )}
        {modo !== "semEmail" && (
          <button onClick={() => setModo("semEmail")} className="underline hover:text-white">não lembro o e-mail</button>
        )}
      </div>

      <p className="mt-6 border-t border-white/10 pt-4 text-xs text-white/40">
        O escritório não vê a sua senha. Seus dados são usados apenas para
        elaborar o que você pedir, conforme a Política de Privacidade.
      </p>
    </section>
  );
}
