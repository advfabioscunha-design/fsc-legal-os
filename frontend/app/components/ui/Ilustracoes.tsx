/* ILUSTRAÇÕES DAS ÁREAS
 *
 * Desenhadas em código, não baixadas de banco de imagem. Três motivos,
 * e nenhum deles é economia:
 *
 *   1. Foto de banco de imagem em site de advocacia é reconhecível de
 *      longe. O martelo sobre a mesa de mogno, o aperto de mão genérico:
 *      o visitante já viu aquilo em vinte sites e o efeito é o contrário
 *      do pretendido, porque comunica que não houve cuidado.
 *   2. Vetor não pesa, não desfoca em tela grande e acompanha a cor da
 *      marca sem precisar de tratamento.
 *   3. É do escritório. Não há licença para renovar nem rosto de
 *      desconhecido representando um cliente.
 *
 * A linguagem é a mesma nas quatro: traço fino, geometria, um ponto de
 * azul elétrico onde está o assunto. Repetição é o que faz um conjunto
 * de desenhos virar identidade em vez de quatro desenhos.
 */

const traco = {
  fill: "none",
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

/* Direito bancário: as parcelas que não fecham com o contrato. */
export function IlustraBancario({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} aria-hidden="true">
      <rect x="10" y="22" width="76" height="52" rx="6"
        stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <path d="M10 36h76" stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <rect x="20" y="46" width="26" height="4" rx="2" fill="currentColor" opacity=".28" />
      <rect x="20" y="56" width="18" height="4" rx="2" fill="currentColor" opacity=".28" />
      <path d="M56 62l7-9 6 6 11-15" stroke="#2D7DD2" strokeWidth="3" {...traco} />
      <circle cx="80" cy="44" r="4" fill="#2D7DD2" />
    </svg>
  );
}

/* Distrato: a planta do imóvel que não veio. */
export function IlustraImobiliario({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} aria-hidden="true">
      <path d="M16 44L48 20l32 24" stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <path d="M24 42v32h48V42" stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <rect x="40" y="54" width="16" height="20" rx="1"
        stroke="#2D7DD2" strokeWidth="3" {...traco} />
      <path d="M62 30h12v10" stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <circle cx="48" cy="64" r="1.6" fill="#2D7DD2" />
    </svg>
  );
}

/* Execução fiscal: a certidão e o prazo. */
export function IlustraFiscal({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} aria-hidden="true">
      <path d="M24 14h34l16 16v52a4 4 0 0 1-4 4H24a4 4 0 0 1-4-4V18a4 4 0 0 1 4-4z"
        stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <path d="M58 14v16h16" stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <rect x="30" y="44" width="30" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <rect x="30" y="54" width="22" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <circle cx="66" cy="66" r="14" stroke="#2D7DD2" strokeWidth="3" {...traco} />
      <path d="M66 59v7l5 3" stroke="#2D7DD2" strokeWidth="3" {...traco} />
    </svg>
  );
}

/* Recuperação de consumo: a conta de energia que veio fora da curva. */
export function IlustraEnergia({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} aria-hidden="true">
      <rect x="18" y="16" width="44" height="64" rx="5"
        stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <rect x="28" y="30" width="24" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <rect x="28" y="40" width="18" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <rect x="28" y="50" width="22" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <path d="M72 28l-12 22h10l-6 20" stroke="#2D7DD2" strokeWidth="3.5" {...traco} />
    </svg>
  );
}

/* Busca e apreensão: o prazo de defesa. */
export function IlustraBuscaApreensao({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} aria-hidden="true">
      <path d="M48 12l28 10v24c0 18-12 30-28 38-16-8-28-20-28-38V22z"
        stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <path d="M38 48l8 8 16-17" stroke="#2D7DD2" strokeWidth="3.5" {...traco} />
    </svg>
  );
}

/* Contratos sob medida: o documento assinado. */
export function IlustraContrato({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} aria-hidden="true">
      <rect x="22" y="12" width="52" height="66" rx="5"
        stroke="currentColor" strokeWidth="2" opacity=".28" {...traco} />
      <rect x="32" y="26" width="32" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <rect x="32" y="36" width="26" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <rect x="32" y="46" width="30" height="3.5" rx="1.75" fill="currentColor" opacity=".28" />
      <path d="M32 64c6-6 10 4 16-2s10 2 16-4" stroke="#2D7DD2" strokeWidth="3" {...traco} />
    </svg>
  );
}

/* Marca d'água geométrica do hero. Fundo, não figura: fica atrás do
   texto e não disputa atenção com ele. */
export function MalhaHero({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 600 600" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2D7DD2" stopOpacity=".5" />
          <stop offset="100%" stopColor="#4361EE" stopOpacity="0" />
        </linearGradient>
      </defs>
      <circle cx="300" cy="300" r="250" stroke="url(#g1)" strokeWidth="1" fill="none" />
      <circle cx="300" cy="300" r="185" stroke="url(#g1)" strokeWidth="1" fill="none" />
      <circle cx="300" cy="300" r="120" stroke="url(#g1)" strokeWidth="1" fill="none" />
      <path d="M50 300h500M300 50v500" stroke="url(#g1)" strokeWidth="1" />
      <circle cx="300" cy="180" r="4" fill="#2D7DD2" opacity=".7" />
      <circle cx="420" cy="300" r="3" fill="#4361EE" opacity=".6" />
      <circle cx="300" cy="420" r="3" fill="#2D7DD2" opacity=".5" />
    </svg>
  );
}
