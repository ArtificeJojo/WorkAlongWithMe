import { NextResponse } from "next/server";
import { pool } from "@/lib/db";

// GET /api/health — quick check that Tiger Data is connected and seeded.
export async function GET() {
  try {
    const { rows } = await pool.query("SELECT count(*)::int AS heroes FROM profiles");
    return NextResponse.json({ ok: true, heroes: rows[0].heroes });
  } catch (err: any) {
    return NextResponse.json({ ok: false, error: err?.message ?? String(err) }, { status: 500 });
  }
}
