/* TERMOS DE USO DA PLATAFORMA

   Existe porque o aceite, na entrada, precisa apontar para alguma
   coisa. Caixa marcada em cima de um link que não abre não é aceite —
   é um formulário com um campo a mais.

   O documento separa duas coisas que o cliente costuma confundir, e é
   essa confusão que gera reclamação depois: usar a plataforma não é
   contratar o escritório. A contratação tem contrato próprio, com
   honorários e objeto definidos. Enquanto ele não existe, o que há
   aqui é um canal de atendimento.

   A redação segue o Provimento 205/2021 do CFOAB: nada de promessa de
   resultado, nada de captação, nada de mercantilização. */

export const metadata = {
  title: "Termos de Uso | FC Advocacia",
  description:
    "Regras de uso da plataforma de atendimento e acompanhamento da FC Advocacia.",
};

const ATUALIZADO = "2 de outubro de 2026";

export default function Termos() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-wide text-gold">
        FC Advocacia · Dr. Fábio Silva Cunha · OAB/RO 10.849
      </p>
      <h1 className="mt-1 text-3xl font-bold text-navy">Termos de Uso</h1>
      <p className="mt-1 text-sm text-charcoal/50">Atualizados em {ATUALIZADO}</p>

      <div className="mt-8 space-y-7 text-[15px] leading-relaxed text-charcoal/80">
        <section>
          <h2 className="text-lg font-bold text-navy">1. O que é esta plataforma</h2>
          <p className="mt-2">
            É o canal digital pelo qual o escritório atende, recebe documentos,
            elabora o que foi contratado e mostra o andamento do seu caso. O
            responsável é <b>Fábio Silva Cunha</b>, advogado inscrito na OAB/RO sob
            o nº 10.849. Contato: <b>adv.fabios.cunha@gmail.com</b>.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">
            2. Criar acesso não é contratar o escritório
          </h2>
          <p className="mt-2">
            Esta é a parte mais importante destes termos. Ter conta aqui, conversar
            pelo chat ou pedir um orçamento <b>não cria relação de advogado e
            cliente</b>. Essa relação nasce com um <b>contrato de honorários
            específico</b>, que descreve o serviço, o valor e as condições, assinado
            pelas duas partes. Enquanto esse contrato não existir, não há prazo
            sendo controlado, processo sendo acompanhado nem providência sendo
            tomada em seu nome.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">3. O que o escritório não promete</h2>
          <p className="mt-2">
            Nenhuma informação desta plataforma é promessa de resultado. O
            advogado se obriga a atuar com técnica e diligência, não a garantir
            desfecho — e quem garante resultado em matéria jurídica está infringindo
            o Código de Ética e Disciplina da OAB. Orientações gerais aqui prestadas
            não substituem a análise do seu caso concreto, com os seus documentos.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">4. A sua conta</h2>
          <p className="mt-2">
            O acesso é pessoal e intransferível. Você é responsável por manter a
            senha em sigilo — ou, se entrou com a conta Google, por proteger essa
            conta. Avise o escritório imediatamente se desconfiar que alguém mais
            teve acesso. O que for feito pela sua conta presume-se feito por você.
          </p>
          <p className="mt-2">
            Os dados que você informa devem ser verdadeiros e atuais. Documento
            jurídico carrega nome, CPF e endereço: dado errado aqui vira defeito no
            documento, e o problema costuma aparecer no pior momento — no cartório,
            no banco ou no processo.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">5. O que não pode ser feito aqui</h2>
          <p className="mt-2">
            Enviar documento falso ou adulterado; usar a plataforma para fim ilícito;
            tentar acessar área ou caso de outra pessoa; automatizar acessos,
            raspar conteúdo ou sobrecarregar o sistema; publicar conteúdo ofensivo
            ou que viole direito de terceiro. O descumprimento permite ao escritório
            suspender o acesso, sem prejuízo das providências cabíveis.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">6. Documentos e conteúdo</h2>
          <p className="mt-2">
            O que você envia continua sendo seu. Você autoriza o escritório a
            armazenar e usar esse material <b>para atender o que você pediu</b> e
            para cumprir obrigações legais da profissão — e para nada além disso.
            As peças, contratos e pareceres elaborados pelo escritório são obra
            intelectual protegida (Lei 9.610/1998): o seu uso é livre para a sua
            própria finalidade, e a reprodução comercial depende de autorização.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">7. Uso de inteligência artificial</h2>
          <p className="mt-2">
            O escritório usa ferramentas de inteligência artificial para organizar
            informação, redigir minutas e acelerar o atendimento. <b>Nenhum documento
            sai sem revisão humana do advogado responsável</b>, que responde pelo
            conteúdo. A tecnologia é instrumento de trabalho; a responsabilidade
            técnica continua sendo de quem assina.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">8. Sigilo</h2>
          <p className="mt-2">
            Tudo o que você escreve e envia está coberto pelo sigilo profissional
            (art. 7º, II, do Estatuto da Advocacia, e art. 25 e seguintes do Código
            de Ética). O sigilo é dever do advogado, não favor, e permanece mesmo
            que a contratação não se concretize.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">9. Disponibilidade</h2>
          <p className="mt-2">
            A plataforma é mantida com cuidado, mas pode ficar fora do ar por
            manutenção ou falha de terceiros. <b>Prazo processual não se controla
            por aqui</b>: o controle é do escritório, pelos sistemas oficiais. A
            indisponibilidade da plataforma não suspende nem transfere obrigação
            sua nem do escritório.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">10. Comunicações</h2>
          <p className="mt-2">
            Os avisos do escritório saem por e-mail, WhatsApp e pela própria
            plataforma, nos contatos que você cadastrou — por isso manter o telefone
            atualizado importa. O escritório <b>não envia propaganda</b> por esses
            canais: as mensagens tratam do seu atendimento, do seu documento ou do
            seu processo.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">11. Dados pessoais</h2>
          <p className="mt-2">
            O tratamento dos seus dados segue a{" "}
            <a href="/privacidade" className="font-semibold text-navy underline underline-offset-4">
              Política de Privacidade
            </a>
            , que é parte destes termos e explica o que é coletado, por quê, por
            quanto tempo e como exercer os seus direitos (Lei 13.709/2018).
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">12. Encerrar o acesso</h2>
          <p className="mt-2">
            Você pode pedir o encerramento da conta a qualquer tempo pelo e-mail
            acima. Alguns registros são mantidos mesmo assim, pelo tempo que a lei
            exige: documentos de processo, registros contábeis e os de conexão
            previstos no Marco Civil da Internet (Lei 12.965/2014, art. 15).
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">13. Mudanças nestes termos</h2>
          <p className="mt-2">
            Se houver alteração relevante, o escritório avisa pelos seus canais e
            pede novo aceite no primeiro acesso seguinte. A data no alto desta
            página mostra a versão vigente.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-navy">14. Lei aplicável e foro</h2>
          <p className="mt-2">
            Aplica-se a lei brasileira. Fica eleito o foro do domicílio do
            consumidor para as controvérsias oriundas destes termos, conforme o
            Código de Defesa do Consumidor.
          </p>
        </section>
      </div>

      <p className="mt-10 border-t border-black/10 pt-5 text-sm text-charcoal/50">
        Dúvida sobre qualquer ponto acima? Escreva para{" "}
        <b>adv.fabios.cunha@gmail.com</b> antes de aceitar. Preferimos explicar
        agora do que resolver depois.
      </p>
    </main>
  );
}
