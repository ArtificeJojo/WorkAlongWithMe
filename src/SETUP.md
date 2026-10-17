# Work Along With Me — setup

This folder is a complete, ready-to-run Next.js project. You need Node.js
installed (`node -v` should print v20 or newer; get it from nodejs.org if not).

```
app/page.tsx                       # temporary home page with a database check
app/layout.tsx, app/globals.css    # page shell + Tailwind
app/api/profile/route.ts           # save / load a hero
app/api/matches/route.ts           # top matches
app/api/health/route.ts            # "is the database working?" check
lib/db.ts                          # Tiger Data connection
lib/profiles.ts                    # load profiles
lib/matching.ts                    # rule-based matching + privacy
lib/quests.ts                      # 🐊 Kanban Swamp + "Choose your powers"
lib/questClient.ts                 # finishQuest() for the game's finale screen
db/schema.sql, db/seed.sql         # paste into the Tiger Data console
tests/                             # 64 automated tests
package.json                       # packages + npm scripts
```

## 1. Install
Open this folder in VS Code (File → Open Folder), open a terminal
(Terminal → New Terminal) and run:
```
npm install
```

## 2. Connect
Create a file named `.env.local` in this folder, right next to `package.json`
(see `.env.local.example`), with one line:
```
DATABASE_URL=postgres://...your Tiger Data connection string...
```
Never commit or share this file (it's already in `.gitignore`).

## 3. Create the tables
In the Tiger Data console, open the SQL editor and run `db/schema.sql`, then `db/seed.sql`.
(Both are safe to run again.) If you ran an older schema.sql earlier, also run
`db/migrations/002_quest_badges.sql` once.

## 4. Check the database works
Run `npm run dev`, then open http://localhost:3000
The home page should say **✅ Connected to Tiger Data. 12 heroes are waiting in the Tavern.**
(If it says ❌, it shows what to check. Changed `.env.local`? Stop `npm run dev` with
Ctrl+C and start it again.)

## 5. Check Kanban Swamp works

### Automated (recommended)
```
npm test
```
You should see **64 passed**. To run only the Kanban Swamp checks:
```
npx vitest run kanban-swamp
```
That plays the whole quest through your real API and Tiger Data database:
hero setup → all 4 scenes → finale → badge → finale summary → matches. It also
saves **every single choice** in every scene, so if someone changes a choice's
value in `lib/quests.ts` and the database won't accept it, a test fails and names
the exact scene and choice. Test heroes are named `__test__` and deleted afterwards.

With no `DATABASE_URL`, the database tests are skipped ("29 passed | 35 skipped").
That means the logic is fine but the database isn't connected yet.

### By hand (while `npm run dev` is running)
Open a second terminal and play the quest yourself:
```
# 1. Hero setup: creates a hero and returns its user_id
curl -s -X POST localhost:3000/api/profile -H "Content-Type: application/json" \
  -d '{"displayName":"Me","heroName":"Me the Swamp Hero","avatar":"gator","answers":{"roles":["builder","designer"]}}'

# 2. Finish Kanban Swamp (paste the user_id from step 1)
curl -s -X POST localhost:3000/api/profile -H "Content-Type: application/json" \
  -d '{"userId":"PASTE_ID","answers":{"task_format":"cards","task_size":"bite_sized","pacing":"checkins","info_styles":["visual"]},"completedQuest":"kanban_swamp"}'

# 3. See your matches
curl -s "localhost:3000/api/matches?userId=PASTE_ID"
```
Step 2 should show your answers and `"completed_quests":["kanban_swamp"]`.
Step 3 should list 3 heroes with reasons like "You both like small check-ins along the way".
You can also see the saved row in the Tiger Data console: `SELECT * FROM profiles;`

If a test or step fails, paste the error message to Claude (never the password).

## How the game screens use it

`lib/quests.ts` holds the whole quest: every scene's title, Chomp's lines, the
choices (emoji, label, reaction) and which database field each scene fills. The
screens should read from `KANBAN_SWAMP` and `CHOOSE_POWERS` instead of hard-coding
text, so the story and the database never drift apart.

| Scene | Field | Values |
|---|---|---|
| Choose Your Powers (hero setup) | `roles` (pick up to 2) | builder, designer, researcher, presenter, leader |
| 1. Build Your Workbench | `task_format` | list, cards, checklist |
| 2. MEGA-BUG Rises! | `task_size` | large, bite_sized |
| 3. The Launch Bridge | `pacing` | single_deadline, checkins, flexible |
| 4. The Locked Gate | `info_styles` (pick 1) | written, visual, verbal, demonstration |
| Finale | `completed_quests` | adds kanban_swamp → Swamp Launcher badge |

**Hero setup (first screen):**
```js
import { finishQuest } from "@/lib/questClient";
// saves name, avatar and powers, and remembers the hero in this browser
await fetch("/api/profile", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ displayName, heroName, avatar, answers: { roles } }),
}).then((r) => r.json()).then(({ profile }) => localStorage.setItem("heroId", profile.user_id));
```

**Kanban Swamp finale:**
```js
import { finishQuest } from "@/lib/questClient";
import { KANBAN_SWAMP, summarize } from "@/lib/quests";

// answers built up as the student taps through the scenes, e.g.
// { task_format: "cards", task_size: "bite_sized", pacing: "checkins", info_styles: ["visual"] }
const lines = summarize(KANBAN_SWAMP, answers); // the "You work best with..." mirror card
const profile = await finishQuest({ questId: KANBAN_SWAMP.id, answers });
// profile.completed_quests includes "kanban_swamp" → show the Swamp Launcher badge
```
A skipped scene can be saved as `null` (or `[]` for the gate).

**Tavern matches:**
```js
const { matches } = await (await fetch(`/api/matches?userId=${heroId}`)).json();
// each match: { hero: {...public fields only}, score, reasons: ["You both prefer ...", ...] }
```
The `reasons` list is what you hand to Gemini to write the friendly explanation.

## Privacy rules (already built in)
- `public`: shown on the hero card and used for matching
- `after_match`: used for matching, never shown or explained before a group forms
- `private`: never used or shown
- Defaults: processing time, feedback style and cool-down are `after_match`; everything else is `public`.

## Before real use
There is no login yet: anyone with a hero's id can load it. Fine for the demo; add real auth afterwards.
