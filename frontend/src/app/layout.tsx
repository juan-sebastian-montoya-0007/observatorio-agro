import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";


export const metadata: Metadata = {
  title: "EVA Explorer",
  description: "Consulta pública de las Evaluaciones Agropecuarias Municipales de Colombia",
};


export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es-CO">
      <body>{children}</body>
    </html>
  );
}
