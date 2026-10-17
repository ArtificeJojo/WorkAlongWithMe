"use client";

import { useEffect, useState } from "react";
import { KANBAN_SWAMP } from "@/lib/quests";

type Health = { ok: true; heroes: number } | { ok: false; error: string } | null;

// Temporary home page: shows whether Tiger Data is connected.
// Replace with the Gate (welcome + accessibility settings) when the game screens are built.
export default function Home() {
  const [health, setHealth] = useState<Health>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setHealth({ ok: false, error: String(e) }));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-6 px-4 py-12">
      <p className="text-sm uppercase tracking-widest opacity-70">Welcome to the Land of Cooooode</p>
      <h1 className="text-4xl font-bold">Work Along With Me</h1>
      <p className="text-lg">
        First quest: <strong>🐊 {KANBAN_SWAMP.name}</strong>, with {KANBAN_SWAMP.scenes.length} scenes.
      </p>

      <section className="rounded-2xl border border-current/20 p-5" aria-live="polite">
        <h2 className="mb-2 font-semibold">Database check</h2>
        {health === null && <p>Checking Tiger Data…</p>}
        {health?.ok === true && (
          <p>✅ Connected to Tiger Data. {health.heroes} heroes are waiting in the Tavern.</p>
        )}
        {health?.ok === false && (
          <div className="space-y-2">
            <p>❌ Not connected yet.</p>
            <p className="text-sm opacity-80">
              Make sure <code>.env.local</code> is next to <code>package.json</code> with your{" "}
              <code>DATABASE_URL</code>, that you ran <code>db/schema.sql</code> and <code>db/seed.sql</code> in
              Tiger Data, and that you restarted <code>npm run dev</code>.
            </p>
            <details className="text-sm opacity-80">
              <summary>Error details</summary>
              <code className="break-all">{health.error}</code>
            </details>
          </div>
        )}
      </section>
    </main>
  );
}
