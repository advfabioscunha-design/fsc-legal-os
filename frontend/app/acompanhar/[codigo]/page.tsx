"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "../../../lib/supabaseClient";
import BotaoGoogle from "../../components/BotaoGoogle";

// O endereço da API do escritório.
const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* A PORTA DE QUEM CHEGOU PELO WHATSAPP.
 *
 * O cliente conversou pelo WhatsApp, recebeu um link e caiu aqui. Ele
 * não tem login: tem um convite de uso único, amarrado ao cadastro que
 * o escritório já abriu para ele.
 *
 * Aqui ele cria e-mail e senha. O passo seguinte, invisível para ele, é
 * o que faz a página valer: o login novo é amarrado ao cadastro que JÁ
 * EXISTE. Sem isso, ele entraria na plataforma e encontraria a área
 * vazia, porque o caso teria ficado no cadastro antigo.
 *
 * O convite morre no uso. Link de WhatsApp se encaminha, e o segundo a
 * receber não pode assumir o cadastro do primeiro. */

export default function Acompanhar() {
  const { codigo } = useParams<{ codigo: string }>();
  const router = useRouter();

  const [carregando, setCarregando] = useState(true);
  const [valido, setValido] = useState(false);
  const [nome, setNome] = useState("");
  const [recado, setRecado] = useState("");

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confere, setConfere] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/cliente/convite/${codigo}`);
        const j = await r.json().catch(() => ({}));
        setValido(!!j?.valido);
        setNome(j?.primeiro_nome || "");
        setRecado(j?.motivo || "");
      } catch {
        setRecado("Não consegui conferir o convite agora. Tente de novo em instantes.");
      }
      setCarregando(false);
    })();
  }, [codigo]);

  const criar = useCallback(async () => {
    setErro("");
    if (!email.includes("@")) return setErro("Escreva um e-mail válido.");
    if (senha.length < 6) return setErro("A senha precisa de ao menos 6 caracteres.");
    if (senha !== confere) return setErro("As duas senhas não são iguais.");

    setOcupado(true);
    try {
      /* Cria a conta e já entra. O Supabase devolve a sessão no mesmo
         passo quando a confirmação por e-mail está desligada; quando não
         devolve, o login logo abaixo resolve, e é por isso que ele existe
         mesmo parecendo repetido. */
      const { error: erroCriar } = await supabase.auth.signUp({ email, password: senha });
      if (erroCriar && !/already/i.test(erroCriar.message)) {
        setOcupado(false);
        return setErro(erroCriar.message);
      }
      const { data, error: erroEntrar } =
        await supabase.auth.signInWithPassword({ email, password: senha });
      if (erroEntrar || !data?.session) {
        setOcupado(false);
        return setErro(erroEntrar?.message
          || "Conta criada. Entre com o e-mail e a senha que você acabou de cadastrar.");
      }

      /* O PASSO QUE FAZ TUDO ISTO VALER
         Amarra este login ao cadastro que veio do WhatsApp. Falhando
         aqui, o cliente entra numa área vazia, então o erro é dito com
         todas as letras em vez de seguir em frente calado. */
      const v = await fetch(`${API}/api/v1/cliente/vincular`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${data.session.access_token}`,
        },
        body: JSON.stringify({ codigo }),
      });
      const jv = await v.json().catch(() => ({}));
      if (!v.ok) {
        setOcupado(false);
        return setErro(jv?.detail
          || "A conta foi criada, mas não consegui ligar ao seu cadastro. Fale com o escritório pelo WhatsApp.");
      }
      /* Falta o que o cadastro do WhatsApp não tem: o nome completo
         conferido pela própria pessoa e o aceite dos termos. A tela de
         conclusão pergunta, e some sozinha para quem já respondeu. */
      router.push("/entrada/completar?next=%2Fcliente");
    } catch {
      setOcupado(false);
      setErro("Falha de conexão. Tente de novo em instantes.");
    }
  }, [email, senha, confere, codigo, router]);

  const campo = "w-full rounded-lg border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-[#C9A24D]";

  return (
    <main className="min-h-screen bg-[#F6F7F9] px-4 py-10">
      <div className="mx-auto max-w-sm rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
        <p className="text-[11px] font-bold uppercase tracking-wider text-[#C9A24D]">
          FC Advocacia
        </p>

        {carregando ? (
          <p className="mt-4 text-sm text-black/50">Conferindo o seu convite…</p>
        ) : !valido ? (
          <>
            <h1 className="mt-2 text-lg font-bold text-[#0A1628]">
              Este convite não está mais válido
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-black/60">
              {recado || "Peça um novo pelo WhatsApp do escritório."}
            </p>
            <a href="/cliente"
              className="mt-5 block rounded-lg border border-black/15 px-4 py-2.5 text-center text-sm font-semibold text-[#0A1628]">
              Já tenho acesso, quero entrar
            </a>
          </>
        ) : (
          <>
            <h1 className="mt-2 text-lg font-bold text-[#0A1628]">
              {nome ? `${nome}, crie o seu acesso` : "Crie o seu acesso"}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-black/60">
              É uma vez só. Depois disso você acompanha o andamento, lê os
              documentos e fala com o escritório pelo mesmo lugar.
            </p>

            {/* O CAMINHO DE UM CLIQUE

                Quem chega aqui está no celular, veio de uma conversa de
                WhatsApp e não quer inventar senha. Com o Google ele
                entra direto, e o convite viaja junto: a conta nova cai
                no cadastro que o escritório já abriu, com o caso dele
                dentro. Sem isso ele entraria numa área vazia. */}
            <div className="mt-5">
              <BotaoGoogle convite={codigo} destino="/cliente"
                rotulo="Entrar com o Google" />
              <div className="mt-4 flex items-center gap-3">
                <span className="h-px flex-1 bg-black/10" />
                <span className="text-[10px] uppercase tracking-wider text-black/35">
                  ou crie uma senha
                </span>
                <span className="h-px flex-1 bg-black/10" />
              </div>
            </div>

            <div className="mt-4 space-y-2.5">
              <input type="email" value={email} inputMode="email"
                autoComplete="email" placeholder="seu e-mail"
                onChange={(e) => setEmail(e.target.value)} className={campo} />
              <input type="password" value={senha} autoComplete="new-password"
                placeholder="crie uma senha"
                onChange={(e) => setSenha(e.target.value)} className={campo} />
              <input type="password" value={confere} autoComplete="new-password"
                placeholder="repita a senha"
                onChange={(e) => setConfere(e.target.value)} className={campo} />
            </div>

            {erro && (
              <p className="mt-3 rounded-lg bg-[#E57373]/10 px-3 py-2 text-[12px] leading-relaxed text-[#B3261E]">
                {erro}
              </p>
            )}

            <button onClick={criar} disabled={ocupado}
              className="mt-4 w-full rounded-lg bg-[#C9A24D] px-4 py-3 text-sm font-bold text-[#0A1628] disabled:opacity-40">
              {ocupado ? "Criando…" : "Criar acesso e ver meu caso"}
            </button>

            <p className="mt-4 text-[11px] leading-relaxed text-black/40">
              O seu caso já está cadastrado no escritório. A senha serve para
              que só você consiga abrir o que é seu.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
