"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

type Par = {
  indice: number; texto: string;
  alinhamento: "left" | "center" | "right" | "justify";
  negrito: boolean; vazio: boolean;
};
type Doc = {
  id: string; caso_id: string; tipo: string; titulo: string; status: string;
  foro: string | null; local_data: string | null; tipo_acao: string | null;
  enviado_em: string | null; assinado_em: string | null;
};

const ROTULO: Record<string, string> = {
  EM_REVISAO: "Em revisão", APROVADO: "Aprovado",
  ENVIADO: "Com o cliente para assinar", ASSINADO: "Assinado", CANCELADO: "Cancelado",
};

export default function EditorDocumento() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [pars, setPars] = useState<Par[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [sujo, setSujo] = useState(false);
  const erroRef = useRef("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/v1/documentos-assinatura/${id}/conteudo`);
      if (!r.ok) { erroRef.current = "Não foi possível abrir este documento."; return; }
      const d = await r.json();
      setDoc(d.documento);
      setPars(d.paragrafos);
      setSujo(false);
    } catch { erroRef.current = "Falha de conexão."; }
    finally { setCarregando(false); }
  }, [id]);

  useEffect(() => { carregar(); }, [carregar]);

  // avisa antes de fechar a aba com alteração não salva
  useEffect(() => {
    const h = (e: BeforeUnloadEvent) => { if (sujo) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [sujo]);

  function mudar(indice: number, texto: string) {
    setPars((ps) => ps.map((p) => (p.indice === indice ? { ...p, texto } : p)));
    setSujo(true);
  }

  async function salvar(silencioso = false) {
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/documentos-assinatura/${id}/conteudo`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paragrafos: pars.map((p) => ({ indice: p.indice, texto: p.texto })) }),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { setAviso(d.detail || "Não foi possível salvar."); return false; }
      setSujo(false);
      if (!silencioso) { setAviso("Alterações salvas."); setTimeout(() => setAviso(""), 3000); }
      return true;
    } catch { setAviso("Falha de conexão ao salvar."); return false; }
    finally { setSalvando(false); }
  }

  async function baixar() {
    if (sujo && !(await salvar(true))) return;
    window.open(`${API}/api/v1/documentos-assinatura/${id}/baixar`, "_blank");
  }

  async function enviarAoCliente() {
    if (!window.confirm(
      "Enviar este documento ao cliente para assinatura?\n\n" +
      "Ele recebe pelo chat da plataforma e por e-mail, com orientação para " +
      "baixar, assinar e devolver o arquivo assinado pelo próprio chat."
    )) return;
    setEnviando(true);
    try {
      if (sujo && !(await salvar(true))) return;
      const r = await fetch(`${API}/api/v1/documentos-assinatura/${id}/enviar-cliente`, { method: "POST" });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { setAviso(d.detail || "Não foi possível enviar."); return; }
      const canais = [d.enviado_email ? "e-mail" : null, d.enviado_whatsapp ? "WhatsApp" : null]
        .filter(Boolean).join(" e ");
      setAviso(`Enviado ao cliente pelo chat da plataforma${canais ? ` e por ${canais}` : ""}.`);
      carregar();
    } catch { setAviso("Falha de conexão ao enviar."); }
    finally { setEnviando(false); }
  }

  if (carregando) {
    return <main className="grid min-h-screen place-items-center bg-ice text-charcoal/50">Abrindo o documento…</main>;
  }
  if (!doc) {
    return (
      <main className="grid min-h-screen place-items-center bg-ice">
        <p className="text-charcoal/60">{erroRef.current || "Documento não encontrado."}</p>
      </main>
    );
  }

  const bloqueado = doc.status === "ASSINADO";

  return (
    <main className="min-h-screen bg-ice pb-24 text-charcoal">
      {/* Barra de ações */}
      <header className="sticky top-0 z-20 border-b border-black/5 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-3 px-5 py-3">
          <div className="min-w-0 flex-1">
            <p className="truncate font-serif text-lg font-bold text-navy">{doc.titulo}</p>
            <p className="text-xs text-charcoal/50">
              {ROTULO[doc.status] || doc.status}
              {doc.foro ? ` · foro ${doc.foro}` : ""}
              {doc.local_data ? ` · ${doc.local_data}` : ""}
              {sujo && <span className="ml-2 font-semibold text-amber">alterações não salvas</span>}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {!bloqueado && (
              <button onClick={() => salvar()} disabled={salvando || !sujo}
                className="rounded-xl border border-black/10 px-4 py-2 text-sm font-semibold text-charcoal/70 hover:border-gold disabled:opacity-40">
                {salvando ? "Salvando…" : "Salvar"}
              </button>
            )}
            <button onClick={baixar}
              className="rounded-xl bg-navy px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
              ⬇ Baixar .docx
            </button>
            {!bloqueado && (
              <button onClick={enviarAoCliente} disabled={enviando}
                className="rounded-xl bg-gold px-5 py-2 text-sm font-bold text-navy hover:bg-amber disabled:opacity-50">
                {enviando ? "Enviando…" : "Enviar ao cliente para assinatura"}
              </button>
            )}
          </div>
        </div>
        {aviso && (
          <div className="border-t border-gold/30 bg-gold/10 px-5 py-2 text-center text-xs font-medium text-navy">
            {aviso}
          </div>
        )}
      </header>

      {doc.status === "ENVIADO" && (
        <div className="mx-auto mt-5 max-w-4xl rounded-xl border border-forest/40 bg-forest/10 px-5 py-3 text-sm text-charcoal/80">
          Já está com o cliente para assinar. Ele baixa pelo painel, assina e devolve pelo chat —
          quando chegar, o arquivo assinado aparece na pasta do caso. Se editar agora, envie de novo.
        </div>
      )}
      {bloqueado && (
        <div className="mx-auto mt-5 max-w-4xl rounded-xl border border-black/10 bg-white px-5 py-3 text-sm text-charcoal/70">
          Documento assinado — não pode mais ser alterado.
        </div>
      )}

      {/* Folha do documento */}
      <section className="mx-auto mt-6 max-w-4xl rounded-2xl border border-black/5 bg-white px-8 py-10 shadow-sm sm:px-16 sm:py-14">
        {pars.map((p) => (
          <AutoTextarea key={p.indice} par={p} bloqueado={bloqueado}
            onChange={(t) => mudar(p.indice, t)} />
        ))}
      </section>

      <p className="mx-auto mt-4 max-w-4xl px-5 text-center text-[11px] text-charcoal/45">
        Edite qualquer trecho direto na folha. A formatação do modelo do escritório
        (fonte, recuos, alinhamento) é preservada no arquivo final.
      </p>
    </main>
  );
}

/* Campo que cresce com o texto, parecendo um parágrafo do documento */
function AutoTextarea({ par, bloqueado, onChange }: {
  par: Par; bloqueado: boolean; onChange: (t: string) => void;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const ajustar = useCallback(() => {
    const el = ref.current;
    if (el) { el.style.height = "auto"; el.style.height = `${el.scrollHeight}px`; }
  }, []);
  useEffect(() => { ajustar(); }, [par.texto, ajustar]);

  if (par.vazio) return <div className="h-4" />;

  return (
    <textarea
      ref={ref} value={par.texto} readOnly={bloqueado} rows={1}
      onChange={(e) => { onChange(e.target.value); ajustar(); }}
      spellCheck={false}
      style={{ textAlign: par.alinhamento }}
      className={`mb-3 w-full resize-none overflow-hidden rounded border border-transparent
        bg-transparent px-2 py-1 font-serif text-[15px] leading-relaxed text-charcoal
        outline-none transition hover:border-black/10 focus:border-gold focus:bg-gold/5
        ${par.negrito ? "font-bold" : ""} ${bloqueado ? "cursor-default" : ""}`}
    />
  );
}
