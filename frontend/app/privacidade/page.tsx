/* POLÍTICA DE PRIVACIDADE

   Este é o documento onde a informação sobre a infraestrutura mora. Ela
   saiu do termo de gravação e da cláusula de honorários, onde assustava
   sem informar ,, mas não podia deixar de existir: sem informação sobre o
   caráter internacional do tratamento, o consentimento do cliente não
   alcança essa parte (LGPD, art. 33). Aqui ela fica disponível a quem
   quiser conferir, e o contrato remete a esta página. */

export const metadata = {
  title: "Política de Privacidade | FC Advocacia",
  description:
    "Como a FC Advocacia trata, protege e armazena os dados dos seus clientes.",
};

const ATUALIZADO = "28 de setembro de 2026";

export default function Privacidade() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-wide text-gold">
        FC Advocacia · Dr. Fábio Silva Cunha · OAB/RO 10.849
      </p>
      <h1 className="mt-1 text-3xl font-bold text-navy">Política de Privacidade</h1>
      <p className="mt-1 text-sm text-charcoal/50">Atualizada em {ATUALIZADO}</p>

      <div className="mt-8 space-y-7 text-[15px] leading-relaxed text-charcoal/80">
        <section>
          <h2 className="text-lg font-bold text-navy">1. Quem trata os seus dados</h2>
          <p className="mt-2">
            O responsável pelo tratamento é <b>Fábio Silva Cunha</b>, advogado inscrito na
            OAB/RO sob o nº 10.849, com escritório na Rua Najla Carone Guedert, Palhoça/SC.
            Contato para assuntos de privacidade: <b>adv.fabios.cunha@gmail.com</b>.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">2. Que dados tratamos</h2>
          <p className="mt-2">
            Dados de identificação e qualificação (nome, CPF, estado civil, profissão,
            endereço), dados de contato (e-mail e telefone), os documentos que você envia,
            o histórico das conversas no painel e por e-mail e, quando você autoriza, o
            <b> áudio dos atendimentos por vídeo</b> e a respectiva transcrição. A imagem dos
            atendimentos por vídeo <b>não é gravada nem armazenada</b>.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">3. Por que tratamos</h2>
          <p className="mt-2">
            Para prestar o serviço de advocacia contratado e cumprir obrigações legais e
            regulamentares da profissão. As bases legais são a <b>execução do contrato</b> e
            o <b>exercício regular de direitos em processo</b> (art. 7º, V e VI, da LGPD).
            A gravação de áudio depende de <b>consentimento específico</b>, dado antes de
            cada atendimento e revogável a qualquer tempo.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">4. Como protegemos</h2>
          <ul className="mt-2 space-y-1.5">
            <li>• Banco de dados <b>exclusivo deste escritório</b>, não compartilhado com
              outros escritórios, empresas ou plataformas.</li>
            <li>• <b>Armazenamento criptografado</b> e conexão criptografada entre o seu
              navegador e o sistema.</li>
            <li>• Acesso por <b>credencial individual</b> de cada integrante da equipe, com
              registro de acesso.</li>
            <li>• Isolamento técnico entre clientes: <b>cada pessoa acessa apenas o seu
              próprio processo</b>.</li>
            <li>• Gravações de áudio são arquivadas no seu processo e a <b>cópia no serviço
              de videochamada é apagada</b> em seguida.</li>
            <li>• Tudo sob o <b>sigilo profissional do advogado</b> (art. 34, VII, da Lei
              8.906/94), que é dever legal, não política interna.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">5. Com quem compartilhamos</h2>
          <p className="mt-2">
            Com ninguém, salvo quando indispensável ao cumprimento do mandato, tribunais,
            partes e peritos, no que o processo exigir, ou por determinação legal ou
            judicial. Não vendemos, cedemos nem usamos os seus dados para publicidade.
          </p>
          <p className="mt-2">
            Utilizamos fornecedores de tecnologia para hospedagem, envio de e-mails e
            videochamada, que atuam como <b>operadores</b> e só podem tratar os dados
            conforme nossas instruções. <b>A infraestrutura que hospeda o sistema está
            localizada no exterior</b>, em data centers profissionais, hipótese de
            transferência internacional admitida pelo art. 33 da LGPD, sem redução das
            garantias descritas no item 4.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">6. Por quanto tempo guardamos</h2>
          <p className="mt-2">
            Pelo prazo do processo e pelos prazos legais de guarda aplicáveis à advocacia,
            inclusive para defesa de direitos após o encerramento. Gravações de áudio podem
            ser excluídas antes disso, a seu pedido.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">7. Os seus direitos</h2>
          <p className="mt-2">
            Você pode pedir confirmação do tratamento, acesso, correção, anonimização,
            portabilidade, informação sobre compartilhamentos e <b>revogação do
            consentimento</b> da gravação (arts. 18 e 19 da LGPD). Basta escrever para o
            e-mail do item 1 ou pedir pelo próprio painel. Respondemos no prazo legal.
          </p>
          <p className="mt-2 text-charcoal/60">
            A revogação do consentimento da gravação não afeta o atendimento nem o
            andamento do seu processo.
          </p>
        </section>
      </div>
    </main>
  );
}
