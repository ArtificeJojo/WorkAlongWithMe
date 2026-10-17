import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Work Along With Me",
  description: "A quest through the Land of Cooooode to find a group that works the way you do.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
