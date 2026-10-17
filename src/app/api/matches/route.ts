import { NextResponse } from "next/server";
import { getAllProfiles } from "@/lib/profiles";
import { topMatches } from "@/lib/matching";

// GET /api/matches?userId=...&n=3
// Returns the top matches for a student. Rules pick the matches;
// each match only includes what the other student made public.
export async function GET(req: Request) {
  const params = new URL(req.url).searchParams;
  const userId = params.get("userId");
  const n = Math.min(Math.max(Number(params.get("n")) || 3, 1), 10);
  if (!userId) return NextResponse.json({ error: "userId is required" }, { status: 400 });

  try {
    const all = await getAllProfiles();
    const me = all.find((p) => p.user_id === userId);
    if (!me) return NextResponse.json({ error: "Hero not found. Finish a quest first." }, { status: 404 });
    return NextResponse.json({ matches: topMatches(me, all, n) });
  } catch (err) {
    console.error("Matching failed:", err);
    return NextResponse.json({ error: "Could not find matches" }, { status: 500 });
  }
}
