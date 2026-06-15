/* Botão flutuante de WhatsApp — site-wide.
   Abre a conversa no número OFICIAL do escritório (ligado ao robô,
   que identifica o cliente pelo número e dá andamento no atendimento).
   Configure o número em NEXT_PUBLIC_WHATSAPP_NUMBER (formato DDI+DDD+nº,
   ex.: 5569999999999). */

const NUMERO = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? "";
const MENSAGEM =
  "Olá! Vim pelo site da FSC Advocacia e gostaria de atendimento.";

export default function BotaoWhatsapp() {
  if (!NUMERO) return null; // sem número configurado, não mostra
  const href = `https://wa.me/${NUMERO}?text=${encodeURIComponent(MENSAGEM)}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Falar no WhatsApp"
      className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-[#25D366] px-5 py-4 text-white shadow-lg transition hover:scale-105 hover:bg-[#1ebe5d]"
      style={{ fontFamily: "Inter, sans-serif" }}
    >
      <svg viewBox="0 0 24 24" className="h-6 w-6 fill-current" aria-hidden="true">
        <path d="M.057 24l1.687-6.163a11.867 11.867 0 01-1.587-5.945C.16 5.335 5.495 0 12.05 0a11.82 11.82 0 018.413 3.488 11.82 11.82 0 013.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 01-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 001.51 5.26l-.999 3.648 3.748-.985a9.864 9.864 0 005.392 1.592zm5.913-7.43c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.71.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413z" />
      </svg>
      <span className="hidden text-sm font-semibold sm:inline">Falar no WhatsApp</span>
    </a>
  );
}
