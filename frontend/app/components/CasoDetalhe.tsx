"use client";
import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";
const GRUPOS = ["BANCARIO", "IMOBILIARIO", "TRABALHISTA", "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"];

export default function CasoDetalhe({ casoId, onFechar, onMudou }: { casoId: string; onFechar: () => void; onMudou: () => void }) {
  const [caso, setCaso] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [nota, setNota] = useState("");
  const [solicitacao, setSolicitacao] = useState("");
  const [aviso, setAviso] = useState({ tipo: "AUDIENCIA", titulo: "", mensagem: "" });
  const [avisando, setAvisando] = useState(false);
  const [novaFase, setNovaFase] = useState("");
  const [subindo, setSubindo] = useState(false);
  const [linkNome, setLinkNome] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);

  // campos editáveis
  const [edit, setEdit] = useState({ relato_inicial: "", grupo: "", honorarios: "", numero_processo: "", titulo: "" });
  // cadastro do cliente (o e-mail é a chave do acesso dele à plataforma)
  const CLI_VAZIO = {
    nome: "", email: "", cpf_cnpj: "", whatsapp: "", nacionalidade: "", estado_civil: "",
    profissao: "", rg: "", endereco_rua: "", endereco_numero: "", endereco_complemento: "",
    endereco_bairro: "", endereco_cidade: "", endereco_uf: "", endereco_cep: "",
  };
  const [cli, setCli] = useState<Record<string, string>>(CLI_VAZIO);
  const [gerando, setGerando] = useState("");
  const [cepStatus, setCepStatus] = useState("");
  // guarda o último CEP já consultado: sem isso, cada vez que o campo perde o
  // foco a busca roda de novo e sobrescreve o logradouro que o usuário editou
  const ultimoCep = useRef("");
  const [instrucaoDoc, setInstrucaoDoc] = useState("");

  /* CEP → endereço. Preenche logradouro, bairro, cidade e UF; os campos
     continuam totalmente editáveis depois (o CEP é um atalho, não uma trava). */
  async function buscarCep(valor: string) {
    const n = (valor || "").replace(/\D/g, "");
    if (n.length !== 8) { setCepStatus(""); return; }
    if (n === ultimoCep.current) return;   // mesmo CEP: não mexe no que já está preenchido
    ultimoCep.current = n;
    setCepStatus("buscando…");
    try {
      const r = await fetch(`${API}/api/v1/cep/${n}`);
      if (!r.ok) {
        ultimoCep.current = "";            // deixa tentar de novo depois
        setCepStatus(r.status === 404 ? "CEP não encontrado" : "não foi possível buscar");
        return;
      }
      const d = await r.json();
      setCli((c) => ({
        ...c,
        endereco_cep: d.cep,
        endereco_rua: d.endereco_rua || c.endereco_rua,
        endereco_bairro: d.endereco_bairro || c.endereco_bairro,
        endereco_cidade: d.endereco_cidade || c.endereco_cidade,
        endereco_uf: d.endereco_uf || c.endereco_uf,
      }));
      setCepStatus("endereço preenchido");
      setTimeout(() => setCepStatus(""), 4000);
    } catch { ultimoCep.current = ""; setCepStatus("não foi possível buscar"); }
  }

  async function carregar() {
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/${casoId}`);
      const d = await r.json();
      setCaso(d);
      setEdit({
        relato_inicial: d.relato_inicial || "", grupo: d.grupo || "",
        honorarios: d.honorarios_valor || "", numero_processo: d.numero_processo || "",
        titulo: d.titulo || "",
      });
      const c: Record<string, string> = { ...CLI_VAZIO };
      Object.keys(CLI_VAZIO).forEach((k) => { c[k] = d.clientes?.[k] || ""; });
      setCli(c);
      ultimoCep.current = (c.endereco_cep || "").replace(/\D/g, "");
    } catch { setCaso(null); }
    finally { setCarregando(false); }
  }
  useEffect(() => { carregar(); /* eslint-disable-next-line */ }, [casoId]);

  async function salvarCampos() {
    setSalvando(true);
    try {
      await fetch(`${API}/api/v1/casos/${casoId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(edit),
      });
      if (caso?.clientes?.id) {
        const r = await fetch(`${API}/api/v1/clientes/${caso.clientes.id}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cli),
        });
        const dcli = await r.json().catch(() => ({} as any));
        if (!r.ok) {
          alert(dcli.detail || "Caso salvo, mas o cadastro do cliente não pôde ser atualizado.");
        } else if (dcli?.contato?.campos?.length) {
          const nomes = dcli.contato.campos.map((c: string) => (c === "email" ? "e-mail" : "WhatsApp")).join(" e ");
          const n = dcli.contato.avisos_reenviados || 0;
          alert(`Contato atualizado.\n\nA plataforma já passou a falar no novo ${nomes}: `
            + `enviamos a confirmação para lá e um comunicado de segurança para o endereço antigo.`
            + (n ? `\n\n${n} aviso(s) que estavam sem ciência foram reenviados para o contato novo.` : ""));
        }
      }
      await carregar(); onMudou();
    } finally { setSalvando(false); }
  }

  async function addNota() {
    if (!nota.trim()) return;
    await fetch(`${API}/api/v1/casos/${casoId}/nota`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: nota }),
    });
    setNota(""); carregar();
  }

  async function addLink() {
    if (!linkUrl.trim()) return;
    await fetch(`${API}/api/v1/casos/${casoId}/documentos`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: linkNome || linkUrl, url: linkUrl, tipo: "LINK" }),
    });
    setLinkNome(""); setLinkUrl(""); carregar();
  }

  async function enviarArquivos(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setSubindo(true);
    const erros: string[] = [];
    try {
      for (const f of files) {
        try {
          const fd = new FormData();
          fd.append("arquivo", f);
          const r = await fetch(`${API}/api/v1/casos/${casoId}/documentos/upload`, { method: "POST", body: fd });
          if (!r.ok) {
            const er = await r.json().catch(() => ({} as any));
            erros.push(`${f.name}: ${er.detail || `erro ${r.status}`}`);
          }
        } catch {
          erros.push(`${f.name}: falha de conexão`);
        }
      }
      if (erros.length) alert("Não foi possível enviar:\n\n" + erros.join("\n"));
    } finally {
      setSubindo(false);
      if (fileRef.current) fileRef.current.value = "";
      carregar();
    }
  }

  async function excluirDoc(id: string) {
    if (!window.confirm("Remover este documento? Esta ação não pode ser desfeita.")) return;
    await fetch(`${API}/api/v1/documentos/${id}`, { method: "DELETE" });
    carregar();
  }

  function baixarDoc(id: string) {
    window.open(`${API}/api/v1/documentos/${id}/baixar`, "_blank");
  }

  async function abrirDoc(id: string) {
    try {
      const r = await fetch(`${API}/api/v1/documentos/${id}/url`);
      const d = await r.json();
      if (d.url) window.open(d.url, "_blank");
      else alert("Não foi possível abrir o documento.");
    } catch { alert("Não foi possível abrir o documento."); }
  }

  async function acao(tipo: "suspender" | "arquivar" | "ativar" | "iniciar") {
    let body: any = undefined;
    if (tipo === "suspender" || tipo === "arquivar") {
      const motivo = window.prompt(tipo === "suspender" ? "Motivo da suspensão:" : "Motivo do arquivamento:");
      if (motivo === null) return;
      body = JSON.stringify({ motivo });
    }
    await fetch(`${API}/api/v1/casos/${casoId}/${tipo}`, {
      method: "POST", headers: body ? { "Content-Type": "application/json" } : undefined, body,
    });
    onMudou();
    if (tipo !== "iniciar") onFechar();
    else carregar();
  }

  async function acionarCliente() {
    if (!solicitacao.trim()) return;
    await fetch(`${API}/api/v1/casos/${casoId}/acionar-cliente`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ solicitacao }),
    });
    setSolicitacao(""); carregar();
  }

  const DOCS_MENU = [
    { tipo: "CONTRATO", nome: "Contrato de Honorários" },
    { tipo: "PROCURACAO", nome: "Procuração ad judicia et extra" },
    { tipo: "HIPOSSUFICIENCIA", nome: "Declaração de Hipossuficiência" },
    { tipo: "OUTRO", nome: "Outros" },
  ];
  const ROTULO_DOC: Record<string, string> = Object.fromEntries(DOCS_MENU.map((d) => [d.tipo, d.nome]));

  async function gerarDocumento(tipo: string) {
    if (tipo === "OUTRO") {
      alert("Para 'Outros', use o chat de Elaboração de Contratos e depois anexe o arquivo em Documentos e provas.");
      return;
    }
    setGerando(tipo);
    try {
      const r = await fetch(`${API}/api/v1/casos/${casoId}/documentos-assinatura`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo, instrucao: instrucaoDoc || null }),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { alert(d.detail || "Não foi possível gerar o documento."); return; }
      if (d.ok === false) {
        alert(`${d.mensagem}\n\nComplete o cadastro do cliente acima e salve antes de gerar.`);
        return;
      }
      setInstrucaoDoc("");
      const novoId = d?.documento?.id;
      if (novoId) window.open(`/documento/${novoId}`, "_blank");
      carregar();
    } catch { alert("Falha de conexão ao gerar o documento."); }
    finally { setGerando(""); }
  }

  async function enviarAoCliente(id: string) {
    if (!window.confirm(
      "Enviar este documento ao cliente para assinatura?\n\n" +
      "Ele recebe no chat da plataforma e por e-mail, com orientação para baixar, " +
      "assinar e devolver o arquivo assinado pelo próprio chat."
    )) return;
    const r = await fetch(`${API}/api/v1/documentos-assinatura/${id}/enviar-cliente`, { method: "POST" });
    const d = await r.json().catch(() => ({} as any));
    if (!r.ok) { alert(d.detail || "Não foi possível enviar."); return; }
    const canais = [d.enviado_email ? "e-mail" : null, d.enviado_whatsapp ? "WhatsApp" : null].filter(Boolean).join(" e ");
    alert(`Enviado ao cliente em PDF (anexo no e-mail), pelo chat da plataforma${canais ? ` e por ${canais}` : ""}.`
      + `\n\nEle pode devolver a via assinada respondendo o e-mail ou pelo painel — nos dois casos o arquivo entra na pasta do caso.`
      + (d.pdf === false ? `\n\nATENÇÃO: não foi possível gerar o PDF (${d.pdf_erro || "erro"}). O cliente vai receber o arquivo Word.` : ""));
    carregar();
  }

  async function excluirDocumentoAssin(id: string) {
    if (!window.confirm("Descartar este documento gerado?")) return;
    await fetch(`${API}/api/v1/documentos-assinatura/${id}`, { method: "DELETE" });
    carregar();
  }

  async function enviarAviso() {
    if (!aviso.titulo.trim() || !aviso.mensagem.trim()) {
      alert("Preencha o título e a mensagem do aviso."); return;
    }
    setAvisando(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/${casoId}/avisar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(aviso),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { alert(d.detail || "Não foi possível enviar o aviso."); return; }
      const canais = [d.enviado_whatsapp ? `WhatsApp (${d.origem_ddd})` : null, d.enviado_email ? "e-mail" : null]
        .filter(Boolean).join(" e ");
      alert(canais
        ? `Aviso enviado por ${canais}. Aguardando a ciência do cliente no painel.`
        : `O aviso foi registrado no painel do cliente, mas não saiu por nenhum canal:\n\n${(d.erros || []).join("\n")}`);
      setAviso({ tipo: "AUDIENCIA", titulo: "", mensagem: "" });
      carregar();
    } finally { setAvisando(false); }
  }

  async function reenviarAviso(id: string) {
    await fetch(`${API}/api/v1/avisos/${id}/reenviar`, { method: "POST" });
    carregar();
  }

  async function aprovarEtapa() {
    const r = await fetch(`${API}/api/v1/casos/${casoId}/aprovar-etapa`, { method: "POST" });
    if (!r.ok) { const e = await r.json().catch(() => ({})); alert(e.detail || "Não foi possível avançar."); return; }
    onMudou(); carregar();
  }

  async function acaoHumana() {
    const r = await fetch(`${API}/api/v1/casos/${casoId}/escalar?motivo=DIFICULDADE&detalhe=${encodeURIComponent("Não resolvido — intervenção direta")}`, { method: "POST" });
    if (!r.ok) { alert("Não foi possível escalar neste estágio. Avance/ajuste a etapa antes."); return; }
    onMudou(); onFechar();
  }

  async function retomar() {
    await fetch(`${API}/api/v1/casos/${casoId}/retomar`, { method: "POST" });
    onMudou(); carregar();
  }

  async function moverFase() {
    if (!novaFase) return;
    await fetch(`${API}/api/v1/casos/${casoId}/mover-fase`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fase: novaFase }),
    });
    setNovaFase(""); onMudou(); carregar();
  }

  function baixar() {
    window.open(`${API}/api/v1/casos/${casoId}/download`, "_blank");
  }

  async function excluir() {
    if (!window.confirm("Excluir DEFINITIVAMENTE este caso? Esta ação não pode ser desfeita.")) return;
    await fetch(`${API}/api/v1/casos/${casoId}`, { method: "DELETE" });
    onMudou(); onFechar();
  }

  const ehEscritorio = caso?.clientes?.origem === "ESCRITORIO";
  const situacao = caso?.situacao || "ATIVO";

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onFechar}>
      <div onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-2xl overflow-y-auto bg-[#0F2A44] text-white shadow-2xl">
        {/* header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0F2A44] px-5 py-3">
          <div>
            <p className="text-lg font-bold">{caso?.clientes?.nome ?? "Caso"}</p>
            {caso?.numero_atendimento && (
              <p className="font-mono text-xs tracking-wide text-[#C9A84C]">
                Atendimento nº {caso.numero_atendimento}
                {caso.titulo ? <span className="ml-2 font-sans text-white/60">· {caso.titulo}</span> : null}
              </p>
            )}
            <p className="text-xs text-white/55">
              {situacao !== "ATIVO" && <span className="mr-2 rounded bg-white/15 px-1.5 py-0.5">{situacao}</span>}
              {caso?.estado} {ehEscritorio && <span className="text-[#C9A84C]">· ★ Escritório</span>}
            </p>
          </div>
          <button onClick={onFechar} className="text-white/60 hover:text-white">✕</button>
        </div>

        {carregando ? (
          <p className="p-6 text-white/50">Carregando...</p>
        ) : !caso ? (
          <p className="p-6 text-white/50">Não foi possível carregar o caso.</p>
        ) : (
          <div className="space-y-6 p-5">
            {caso.aguardando_cliente && (
              <div className="rounded-lg border border-[#F39C12]/40 bg-[#F39C12]/10 p-3">
                <p className="text-sm font-semibold text-[#F39C12]">⏸ Fora da produção — aguardando o cliente</p>
                <p className="mt-1 text-sm text-white/75">{caso.aguardando_desc}</p>
                <button onClick={retomar} className="mt-2 rounded-lg bg-[#1DB954] px-4 py-1.5 text-sm font-bold text-white hover:bg-[#17a349]">
                  Cliente respondeu — retomar produção
                </button>
              </div>
            )}

            {/* Dados editáveis */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Cadastro do cliente</h3>
              <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="text-xs text-white/60">Nome
                  <input value={cli.nome} onChange={(e) => setCli({ ...cli, nome: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">E-mail <span className="text-[#C9A84C]">(acesso do cliente à plataforma)</span>
                  <input value={cli.email} onChange={(e) => setCli({ ...cli, email: e.target.value })}
                    type="email" placeholder="cliente@email.com"
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">WhatsApp
                  <input value={cli.whatsapp} onChange={(e) => setCli({ ...cli, whatsapp: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">CPF/CNPJ
                  <input value={cli.cpf_cnpj} onChange={(e) => setCli({ ...cli, cpf_cnpj: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">RG
                  <input value={cli.rg} onChange={(e) => setCli({ ...cli, rg: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Nacionalidade
                  <input value={cli.nacionalidade} onChange={(e) => setCli({ ...cli, nacionalidade: e.target.value })}
                    placeholder="brasileira" className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Estado civil
                  <input value={cli.estado_civil} onChange={(e) => setCli({ ...cli, estado_civil: e.target.value })}
                    placeholder="casada" className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Profissão
                  <input value={cli.profissao} onChange={(e) => setCli({ ...cli, profissao: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">CEP
                  <span className="ml-2 text-[10px] text-[#C9A84C]">{cepStatus}</span>
                  <input value={cli.endereco_cep} inputMode="numeric" maxLength={9} placeholder="76801-100"
                    onChange={(e) => { const v = e.target.value; setCli((c) => ({ ...c, endereco_cep: v })); buscarCep(v); }}
                    onBlur={(e) => buscarCep(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60 sm:col-span-2">Logradouro
                  <input type="text" autoComplete="off" spellCheck={false}
                    value={cli.endereco_rua ?? ""}
                    onChange={(e) => { const v = e.target.value; setCli((c) => ({ ...c, endereco_rua: v })); }}
                    placeholder="Avenida Sete de Setembro"
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white" />
                </label>
                <label className="text-xs text-white/60">Número
                  <input value={cli.endereco_numero} onChange={(e) => setCli({ ...cli, endereco_numero: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Complemento
                  <input value={cli.endereco_complemento} onChange={(e) => setCli({ ...cli, endereco_complemento: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Bairro
                  <input value={cli.endereco_bairro} onChange={(e) => setCli({ ...cli, endereco_bairro: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Cidade <span className="text-white/35">(vira o local e o foro)</span>
                  <input value={cli.endereco_cidade} onChange={(e) => setCli({ ...cli, endereco_cidade: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">UF
                  <input value={cli.endereco_uf} maxLength={2} onChange={(e) => setCli({ ...cli, endereco_uf: e.target.value.toUpperCase() })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
              </div>
              {!cli.email && (
                <p className="mb-3 rounded-lg border border-[#F39C12]/40 bg-[#F39C12]/10 px-3 py-2 text-xs text-[#F39C12]">
                  Sem e-mail cadastrado o cliente não consegue acessar a plataforma para receber
                  pedidos nem enviar documentos. Preencha e salve.
                </p>
              )}

              <p className="mb-4 text-[11px] text-white/45">
                Ao trocar o e-mail ou o WhatsApp aqui, a plataforma passa a falar no
                endereço novo na hora: confirma no contato novo, comunica o antigo por
                segurança e reenvia para lá tudo o que ainda estava sem ciência.
              </p>

              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Informações do caso</h3>
              <label className="mb-3 block text-xs text-white/60">Nome do caso <span className="text-white/40">(é o que o cliente vê junto do nº de atendimento)</span>
                <input value={edit.titulo} onChange={(e) => setEdit({ ...edit, titulo: e.target.value })}
                  placeholder="Ex.: Revisão de contrato bancário — Banco X"
                  className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              </label>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="text-xs text-white/60">Grupo
                  <select value={edit.grupo} onChange={(e) => setEdit({ ...edit, grupo: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm">
                    <option value="">—</option>
                    {GRUPOS.map((g) => <option key={g} value={g}>{g}</option>)}
                  </select>
                </label>
                <label className="text-xs text-white/60">Nº do processo
                  <input value={edit.numero_processo} onChange={(e) => setEdit({ ...edit, numero_processo: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Honorários
                  <input value={edit.honorarios} onChange={(e) => setEdit({ ...edit, honorarios: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
              </div>
              <label className="mt-3 block text-xs text-white/60">Relato / informações coletadas
                <textarea value={edit.relato_inicial} onChange={(e) => setEdit({ ...edit, relato_inicial: e.target.value })} rows={4}
                  className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              </label>
              <button onClick={salvarCampos} disabled={salvando}
                className="mt-2 rounded-lg bg-[#C9A84C] px-4 py-2 text-sm font-bold text-[#0A1628] disabled:opacity-50">
                {salvando ? "Salvando..." : "Salvar alterações"}
              </button>
            </section>

            {/* Documentos */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Documentos e provas</h3>
              <ul className="space-y-2">
                {(caso.documentos || []).map((d: any) => {
                  const url = (d.storage_path || "").startsWith("http") ? d.storage_path : null;
                  return (
                    <li key={d.id} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-[#0A1628]/50 px-3 py-2 text-sm">
                      <span className="truncate">
                        {d.enviado_por === "CLIENTE" && (
                          <span className="mr-2 rounded bg-[#1DB954]/20 px-1.5 py-0.5 text-[10px] font-bold text-[#1DB954]">CLIENTE</span>
                        )}
                        {d.observacao || d.tipo}
                      </span>
                      <span className="flex shrink-0 items-center gap-3">
                        {url
                          ? <a href={url} target="_blank" rel="noreferrer" className="text-[#C9A84C] hover:underline">abrir</a>
                          : <>
                              <button onClick={() => abrirDoc(d.id)} className="text-[#C9A84C] hover:underline">abrir</button>
                              <button onClick={() => baixarDoc(d.id)} className="text-white/70 hover:text-white hover:underline">baixar</button>
                            </>}
                        <button onClick={() => excluirDoc(d.id)} className="text-[#C0392B] hover:underline">excluir</button>
                      </span>
                    </li>
                  );
                })}
                {(caso.documentos || []).length === 0 && <li className="text-xs text-white/40">Nenhum documento ainda.</li>}
              </ul>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-dashed border-white/15 p-3">
                  <p className="mb-2 text-xs text-white/60">Anexar do computador (vários de uma vez)</p>
                  <input ref={fileRef} type="file" multiple onChange={enviarArquivos} className="hidden" id="upload-arq" />
                  <label htmlFor="upload-arq" className="inline-block cursor-pointer rounded bg-[#C9A84C] px-3 py-1.5 text-xs font-bold text-[#0A1628] hover:bg-[#d8b95e]">
                    + Adicionar arquivo(s)
                  </label>
                  {subindo && <span className="ml-2 text-xs text-white/60">enviando…</span>}
                </div>
                <div className="rounded-lg border border-dashed border-white/15 p-3">
                  <p className="mb-1 text-xs text-white/60">Anexar link (Drive/nuvem)</p>
                  <input value={linkNome} onChange={(e) => setLinkNome(e.target.value)} placeholder="Nome (opcional)"
                    className="mb-1 w-full rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-xs" />
                  <div className="flex gap-1">
                    <input value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://..."
                      className="flex-1 rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-xs" />
                    <button onClick={addLink} className="rounded bg-[#C9A84C] px-2 py-1 text-xs font-bold text-[#0A1628]">+</button>
                  </div>
                </div>
              </div>
            </section>

            {/* Acionar cliente */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Pedir documento / informação ao cliente</h3>
              <p className="mb-2 text-xs text-white/55">
                O pedido cai na <b className="text-white/75">caixa de mensagens do cliente</b>, dentro do cadastro dele.
                Ele anexa o arquivo ou tira a foto pelo próprio chat e, ao enviar, o documento aparece
                nesta pasta e o caso volta sozinho para a produção.
              </p>

              {(caso.solicitacoes || []).length > 0 && (
                <ul className="mb-3 space-y-1">
                  {(caso.solicitacoes || []).map((s: any) => (
                    <li key={s.id} className="flex items-start gap-2 rounded-lg border border-white/10 bg-[#0A1628]/50 px-3 py-2 text-sm">
                      <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        s.status === "PENDENTE" ? "bg-[#F39C12]/20 text-[#F39C12]" : "bg-[#1DB954]/20 text-[#1DB954]"
                      }`}>{s.status === "PENDENTE" ? "AGUARDANDO" : "ATENDIDA"}</span>
                      <span className="text-white/75">{s.descricao}</span>
                    </li>
                  ))}
                </ul>
              )}

              <textarea value={solicitacao} onChange={(e) => setSolicitacao(e.target.value)} rows={2} placeholder="Ex.: Enviar RG e comprovante de residência..."
                className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              <button onClick={acionarCliente} className="mt-2 rounded-lg bg-[#2D7DD2] px-4 py-2 text-sm font-bold text-white hover:bg-[#256bb3]">Enviar ao cliente</button>
            </section>

            {/* Gerar documento a partir dos modelos do escritório */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Gerar documento</h3>
              <p className="mb-2 text-xs text-white/55">
                O agente monta o documento a partir do <b className="text-white/75">modelo oficial do escritório</b>,
                trocando só o que muda: qualificação, objeto conforme o relato, foro e local
                (a cidade do cliente), data e assinatura. O documento <b className="text-white/75">abre
                em outra aba</b> para o senhor ajustar; de lá é só baixar ou enviar ao cliente.
                O cliente recebe <b className="text-white/75">o PDF anexo ao e-mail</b> e devolve
                a via assinada como preferir: respondendo o próprio e-mail ou pelo painel.
                Nos dois casos o arquivo cai aqui, na pasta do caso.
              </p>
              <input value={instrucaoDoc} onChange={(e) => setInstrucaoDoc(e.target.value)}
                placeholder="Orientação para o agente (opcional): ex. incluir pedido de tutela de urgência"
                className="mb-2 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              <div className="mb-3 flex flex-wrap gap-2">
                {DOCS_MENU.map((m) => (
                  <button key={m.tipo} onClick={() => gerarDocumento(m.tipo)} disabled={!!gerando}
                    className="rounded-lg bg-[#C9A84C] px-3 py-2 text-xs font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
                    {gerando === m.tipo ? "Gerando…" : `+ ${m.nome}`}
                  </button>
                ))}
              </div>

              <ul className="space-y-2">
                {(caso.documentos_assinatura || []).map((x: any) => {
                  const cor = x.status === "ASSINADO" ? "#1DB954"
                    : x.status === "ENVIADO" ? "#2D7DD2"
                    : x.status === "APROVADO" ? "#C9A84C" : "#F39C12";
                  const rotuloStatus = x.status === "ENVIADO" ? "COM O CLIENTE"
                    : x.status === "EM_REVISAO" ? "EM REVISÃO" : x.status;
                  return (
                    <li key={x.id} className="rounded-lg border border-white/10 bg-[#0A1628]/50 px-3 py-2 text-sm">
                      <div className="flex items-start justify-between gap-2">
                        <span className="min-w-0">
                          <span className="block font-semibold text-white/85">{ROTULO_DOC[x.tipo] || x.tipo}</span>
                          <span className="block text-xs text-white/45">
                            {x.local_data}{x.foro ? ` · foro ${x.foro}` : ""}
                          </span>
                        </span>
                        <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold"
                          style={{ color: cor, backgroundColor: `${cor}26` }}>{rotuloStatus}</span>
                      </div>
                      {x.tipo_acao && x.tipo === "PROCURACAO" && (
                        <p className="mt-1 text-xs text-white/55">Ação: {x.tipo_acao}</p>
                      )}
                      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                        <a href={`/documento/${x.id}`} target="_blank" rel="noreferrer"
                          className="font-bold text-[#C9A84C] hover:underline">abrir e ajustar</a>
                        <a href={`${API}/api/v1/documentos-assinatura/${x.id}/baixar`} target="_blank" rel="noreferrer"
                          className="text-white/70 hover:text-white hover:underline">baixar .docx</a>
                        <a href={`${API}/api/v1/documentos-assinatura/${x.id}/baixar?formato=pdf`} target="_blank" rel="noreferrer"
                          className="text-white/70 hover:text-white hover:underline">baixar PDF</a>
                        {x.assinado_url && (
                          <a href={`${API}/api/v1/documentos-assinatura/${x.id}/baixar`} target="_blank" rel="noreferrer"
                            className="font-bold text-[#1DB954] hover:underline">baixar assinado</a>
                        )}
                        {x.status !== "ASSINADO" && (
                          <button onClick={() => enviarAoCliente(x.id)} className="font-bold text-[#1DB954] hover:underline">
                            {x.status === "ENVIADO" ? "reenviar ao cliente" : "enviar ao cliente para assinar"}
                          </button>
                        )}
                        {x.status !== "ASSINADO" && (
                          <button onClick={() => excluirDocumentoAssin(x.id)} className="ml-auto text-[#C0392B] hover:underline">descartar</button>
                        )}
                      </div>
                    </li>
                  );
                })}
                {(caso.documentos_assinatura || []).length === 0 && (
                  <li className="text-xs text-white/40">Nenhum documento gerado para este caso.</li>
                )}
              </ul>
            </section>

            {/* Avisar o cliente — audiência, prazo, movimentação */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Avisar o cliente (e-mail + WhatsApp)</h3>
              <p className="mb-2 text-xs text-white/55">
                O aviso sai pelo número do escritório correspondente ao <b className="text-white/75">DDD do cliente</b>
                {" "}(69 → Rondônia, 48 → Santa Catarina, demais → 48) e também por e-mail.
                Fica registrado até o cliente tocar em <b className="text-white/75">“Li e estou ciente”</b> no painel —
                e o sistema reenvia sozinho a cada 24 h enquanto ele não confirmar.
              </p>

              {(caso.avisos || []).length > 0 && (
                <ul className="mb-3 space-y-1">
                  {(caso.avisos || []).slice(0, 6).map((a: any) => (
                    <li key={a.id} className="rounded-lg border border-white/10 bg-[#0A1628]/50 px-3 py-2 text-sm">
                      <div className="flex items-start justify-between gap-2">
                        <span className="min-w-0">
                          <span className="block font-semibold text-white/85">{a.titulo}</span>
                          <span className="block text-xs text-white/50">
                            {a.enviado_whatsapp ? `WhatsApp ${a.numero_origem || ""}` : "WhatsApp ✕"} ·{" "}
                            {a.enviado_email ? "e-mail" : "e-mail ✕"}
                            {a.lembretes > 0 ? ` · ${a.lembretes} lembrete(s)` : ""}
                          </span>
                        </span>
                        {a.ciencia_em ? (
                          <span className="shrink-0 rounded bg-[#1DB954]/20 px-1.5 py-0.5 text-[10px] font-bold text-[#1DB954]">
                            CIENTE {new Date(a.ciencia_em).toLocaleDateString("pt-BR")}
                          </span>
                        ) : (
                          <button onClick={() => reenviarAviso(a.id)}
                            className="shrink-0 rounded bg-[#F39C12]/20 px-1.5 py-0.5 text-[10px] font-bold text-[#F39C12] hover:bg-[#F39C12]/30">
                            SEM CIÊNCIA · reenviar
                          </button>
                        )}
                      </div>
                      {a.erro_envio && <p className="mt-1 text-[11px] text-[#e07a6f]">Falha: {a.erro_envio}</p>}
                    </li>
                  ))}
                </ul>
              )}

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-[160px_1fr]">
                <select value={aviso.tipo} onChange={(e) => setAviso({ ...aviso, tipo: e.target.value })}
                  className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm">
                  <option value="AUDIENCIA">Audiência</option>
                  <option value="MOVIMENTACAO">Movimentação</option>
                  <option value="PRAZO">Prazo</option>
                  <option value="PAGAMENTO">Pagamento</option>
                  <option value="GERAL">Geral</option>
                </select>
                <input value={aviso.titulo} onChange={(e) => setAviso({ ...aviso, titulo: e.target.value })}
                  placeholder="Título (ex.: Audiência marcada para 12/11)"
                  className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              </div>
              <textarea value={aviso.mensagem} onChange={(e) => setAviso({ ...aviso, mensagem: e.target.value })}
                rows={3} placeholder="Escreva em linguagem simples o que o cliente precisa saber e o que ele deve fazer."
                className="mt-2 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              <button onClick={enviarAviso} disabled={avisando}
                className="mt-2 rounded-lg bg-[#2D7DD2] px-4 py-2 text-sm font-bold text-white hover:bg-[#256bb3] disabled:opacity-50">
                {avisando ? "Enviando…" : "Enviar aviso ao cliente"}
              </button>
            </section>

            {/* Histórico / notas */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Histórico do atendimento</h3>
              <div className="max-h-60 space-y-2 overflow-y-auto rounded-lg border border-white/10 bg-[#0A1628]/40 p-3">
                {(caso.mensagens || []).map((m: any) => (
                  <div key={m.id} className="text-sm">
                    <span className={`text-[10px] uppercase ${m.autor === "CLIENTE" ? "text-[#2D7DD2]" : m.autor === "HUMANO" ? "text-[#C9A84C]" : "text-white/40"}`}>{m.autor}</span>
                    <p className="whitespace-pre-wrap text-white/80">{m.conteudo}</p>
                  </div>
                ))}
                {(caso.mensagens || []).length === 0 && <p className="text-xs text-white/40">Sem mensagens.</p>}
              </div>
              <div className="mt-2 flex gap-2">
                <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Acrescentar informação / nota interna"
                  className="flex-1 rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                <button onClick={addNota} className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold hover:bg-white/20">Adicionar</button>
              </div>
            </section>

            {/* Ações */}
            <section className="border-t border-white/10 pt-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <button onClick={baixar} title="Relatório de atendimento em Word + todos os documentos, inclusive os que o cliente enviou"
                  className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold hover:bg-white/20">⬇ Baixar tudo (.zip com relatório + documentos)</button>
                <select value={novaFase} onChange={(e) => setNovaFase(e.target.value)}
                  className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm">
                  <option value="">Mover para fase…</option>
                  {["QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO", "COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO", "PROTOCOLADO"].map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
                <button onClick={moverFase} className="rounded-lg bg-[#2D7DD2] px-3 py-2 text-sm font-semibold text-white hover:bg-[#256bb3]">Mover</button>
              </div>
              <div className="flex flex-wrap gap-2">
                {ehEscritorio && situacao === "ATIVO" && (
                  <button onClick={() => acao("iniciar")} className="rounded-lg bg-[#1DB954] px-4 py-2 text-sm font-bold text-white hover:bg-[#17a349]">
                    ▶ Iniciar na Esteira
                  </button>
                )}
                {situacao === "ATIVO" ? (
                  <>
                    <button onClick={() => acao("suspender")} className="rounded-lg bg-[#F39C12]/20 px-4 py-2 text-sm font-semibold text-[#F39C12] hover:bg-[#F39C12]/30">Suspender</button>
                    <button onClick={() => acao("arquivar")} className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white/80 hover:bg-white/20">Arquivar</button>
                  </>
                ) : (
                  <button onClick={() => acao("ativar")} className="rounded-lg bg-[#1DB954] px-4 py-2 text-sm font-bold text-white hover:bg-[#17a349]">Ativar caso (voltar à esteira)</button>
                )}
                {situacao === "ATIVO" && (
                  <>
                    <button onClick={aprovarEtapa} className="rounded-lg bg-[#1DB954]/20 px-4 py-2 text-sm font-semibold text-[#1DB954] hover:bg-[#1DB954]/30">Aprovar para continuar</button>
                    <button onClick={acaoHumana} className="rounded-lg bg-[#C0392B]/15 px-4 py-2 text-sm font-semibold text-[#e07a6f] hover:bg-[#C0392B]/25">Ação humana (não resolvido)</button>
                  </>
                )}
                <button onClick={excluir} className="ml-auto rounded-lg bg-[#C0392B]/20 px-4 py-2 text-sm font-semibold text-[#C0392B] hover:bg-[#C0392B]/30">Excluir</button>
              </div>
              {caso.situacao_motivo && <p className="mt-2 text-xs text-white/50">Motivo: {caso.situacao_motivo}</p>}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
