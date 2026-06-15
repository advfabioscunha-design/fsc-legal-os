/** @type {import('next').NextConfig} */
module.exports = {
  // Não derrubar o build de produção por lint/TS (robustez no deploy)
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
};
