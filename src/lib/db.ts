import { Pool } from "pg";

// Tiger Data's connection string ends in ?sslmode=require. The pg library treats
// that as "strictly verify the certificate", which overrides the ssl option below
// and fails on many laptops (antivirus or campus Wi-Fi) with
// "self-signed certificate in certificate chain". So we remove the sslmode
// setting from the string and choose the SSL behavior here instead:
// the connection is still encrypted, it just skips the strict certificate check.
function prepareConnection(raw: string | undefined) {
  if (!raw) return { connectionString: raw, isLocal: false };
  const isLocal = /localhost|127\.0\.0\.1/.test(raw);
  try {
    const url = new URL(raw);
    for (const key of ["sslmode", "sslrootcert", "sslcert", "sslkey", "uselibpqcompat"]) {
      url.searchParams.delete(key);
    }
    return { connectionString: url.toString(), isLocal };
  } catch {
    return { connectionString: raw, isLocal };
  }
}

const { connectionString, isLocal } = prepareConnection(process.env.DATABASE_URL);

// One shared connection pool. Reused across hot reloads in dev.
const globalForPg = globalThis as unknown as { pgPool?: Pool };

export const pool =
  globalForPg.pgPool ??
  new Pool({
    connectionString,
    ssl: isLocal ? false : { rejectUnauthorized: false },
    max: 5,
  });

if (process.env.NODE_ENV !== "production") globalForPg.pgPool = pool;
