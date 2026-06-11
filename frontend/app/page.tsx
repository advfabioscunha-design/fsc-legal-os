import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-3xl font-bold">FSC Advocacia</h1>
      <p className="text-slate-600">
        Atendimento digital — Dr. Fábio Silva Cunha (OAB/RO 10.849)
      </p>
      <div className="flex gap-4">
        <Link href="/portal"
              className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white">
          Sou cliente
        </Link>
        <Link href="/crm"
              className="rounded-lg border border-slate-300 px-6 py-3 font-semibold">
          Área do escritório
        </Link>
      </div>
      <footer className="mt-10 text-sm text-slate-500">
        <a href="mailto:contato@fscadvocaciadigital.com.br"
           className="hover:text-blue-600">
          contato@fscadvocaciadigital.com.br
        </a>
      </footer>
    </main>
  );
}
