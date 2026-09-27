# Gerar documentos e colher assinatura digital
**Implantado e testado em 27/09/2026.**

---

## O caminho

```
CRM → abrir o caso → "Gerar documento"
      ├── Contrato de Honorários
      ├── Procuração ad judicia et extra
      ├── Declaração de Hipossuficiência
      └── Outros
                ↓
   O agente usa o MODELO OFICIAL do escritório e troca só o que varia
                ↓
   Documento nasce EM REVISÃO  →  o senhor confere e aprova
                ↓
   "Aprovar e enviar para assinatura"  →  ZapSign
                ↓
   Cliente recebe o link por e-mail, WhatsApp e no painel da plataforma
                ↓
   Assinou → PDF volta para a pasta do caso e o cliente é avisado
```

## O que o agente muda em cada modelo

| Documento | O que é alterado | O que NUNCA muda |
|---|---|---|
| **Contrato de Honorários** | qualificação do contratante · objeto (item 3), redigido conforme o relato · foro (10.1) · local e data · nome e CPF na assinatura | cláusulas de honorários, responsabilidades, prazos — o modelo é lei |
| **Procuração** | qualificação do outorgante · tipo de ação no fecho do item III · local e data · nome como outorgante | os poderes ad judicia et extra |
| **Declaração de Hipossuficiência** | qualificação · local e data · nome e CPF | fundamentos legais e advertência criminal |

**Local e foro seguem o endereço do cliente.** Cliente de Porto Velho gera
"Porto Velho/RO, 27 de setembro de 2026" e foro de Porto Velho/RO. Foro de
eleição no domicílio do consumidor evita a nulidade de ofício que o juízo
costuma declarar quando o contrato elege a comarca do fornecedor.

## Qualificação do cliente

Os modelos exigem nacionalidade, estado civil, profissão e endereço completo.
Esses campos entram por três caminhos, todos já no ar:

- **o cliente** completa em *Meu cadastro* no painel (com aviso do que falta);
- **o escritório** edita no CRM, no bloco *Cadastro do cliente*;
- antes de gerar, o sistema **confere e recusa** se faltar dado, dizendo
  exatamente o quê — nunca gera documento com lacuna.

## Revisão antes de assinar

Nada vai ao cliente sem a sua aprovação. Na pasta do caso cada documento mostra
o status (EM REVISÃO · APROVADO · ENVIADO · ASSINADO), o foro, o local/data e,
na procuração, o tipo de ação. O senhor pode **baixar o .docx**, conferir,
**descartar** e gerar de novo, ou aprovar e enviar.

O campo *Orientação para o agente* permite direcionar a redação do objeto antes
de gerar — por exemplo "incluir pedido de tutela de urgência para suspender os
descontos".

---

## Falta uma coisa: a conta no ZapSign

A geração dos documentos **já funciona**. O envio para assinatura precisa do
token da conta:

1. Crie a conta em **zapsign.com.br** (plano gratuito serve para testar)
2. Entre em **Configurações → Integrações → API**
3. Copie o **API Token**
4. Me mande que eu configuro no servidor (`ZAPSIGN_API_TOKEN`)

Também vou precisar cadastrar o **webhook** lá, apontando para:
```
https://api.fscadvocaciadigital.com.br/webhooks/zapsign
```
É ele que avisa a plataforma quando o cliente assina — sem isso o documento
fica como "ENVIADO" para sempre.

**Preços (setembro/2026):** plano Individual gratuito para começar; o plano
Equipe custa R$ 79,90/mês e cobre 900 documentos por ano. Certificado digital
ICP-Brasil, se quiser, sai a R$ 0,50 por assinatura; biometria facial a R$ 1,50.

---

## Teste executado hoje

Cliente fictício em Porto Velho/RO, caso bancário com relato de tarifas não
contratadas e seguro prestamista.

| Verificação | Resultado |
|---|---|
| Conferência da qualificação | completo, sem pendências |
| Contrato gerado | objeto com 4 pedidos redigidos para o caso; cláusulas do modelo preservadas |
| Foro | Porto Velho/RO (domicílio do cliente) |
| Local e data | Porto Velho/RO, 27 de setembro de 2026 |
| Assinatura | MARIA APARECIDA DE SOUZA · CPF nº 111.444.777-35 |
| Procuração | AÇÃO DECLARATÓRIA DE NULIDADE DE CLÁUSULAS C/C REPETIÇÃO DE INDÉBITO |
| Declaração | qualificação, local, data, nome e CPF corretos |
| Download do .docx | abre no Word com a formatação original intacta |

Os dados do teste foram apagados.

**Um defeito corrigido no caminho:** o download quebrava quando o nome do
arquivo tinha travessão ou acento (cabeçalho HTTP só aceita latin-1). Agora vai
uma versão ASCII para compatibilidade e a versão acentuada em UTF-8, que é a
que o senhor vê ao salvar.

---

## Sobre a opção "Outros"

Por enquanto ela aponta para o chat de Elaboração de Contratos, que já existe na
plataforma, e o arquivo depois é anexado em *Documentos e provas*. Quando o
senhor tiver outros modelos padronizados, é só me mandar os .docx que eu
acrescento ao menu do mesmo jeito que os três primeiros.
