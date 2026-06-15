"use client";
import { createClient } from "@supabase/supabase-js";

// Chave ANON (pública, segura no navegador). Configurar na Vercel:
//   NEXT_PUBLIC_SUPABASE_URL  e  NEXT_PUBLIC_SUPABASE_ANON_KEY
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ""
);
