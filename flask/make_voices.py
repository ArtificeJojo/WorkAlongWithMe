"""Records every spoken line of the quests with Gemini voices, once, into src/audio/.

    python make_voices.py            (run from the flask folder; needs GEMINI_KEY in .env)
    python make_voices.py edge       (free Microsoft Edge neural voices: no key, no limits;
                                      first: pip install edge-tts)

Each character has its own voice and acting direction:
  Chomp    - bright, bubbly and excited
  Ponder   - slow, soft and calm
  The Time Eater - a gravelly, over-the-top cartoon villain
  The tiny bugs - squeaky little voices

The clips are saved as files (plus src/audio/manifest.json), so the quest page plays them instantly
with no waiting and no API calls during a demo. Lines without a clip fall back to the browser's voice.
It is safe to run again: lines that already have a clip are skipped, so only new or changed lines are recorded.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import time
import wave
from os import environ as env
from pathlib import Path

from dotenv import load_dotenv

from quests import QUESTS

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

OUT = Path(__file__).resolve().parent.parent / "src" / "audio"
MODEL = env.get("GEMINI_TTS_MODEL")  # picked automatically when not set

SPEAKERS = {
    "chomp": {
        "voice": "Fenrir",
        "direction": "You are Chomp, an energetic, upbeat cartoon alligator guy in a kids' adventure show. "
                     "Speak fast, bright and bouncy, with big energy, playful emphasis on capital words, and a smile you can hear",
    },
    "ponder": {
        "voice": "Achernar",
        "direction": "You are Ponder, a gentle, sleepy old turtle in a kids' adventure show. "
                     "Speak slowly, softly and calmly, warm and kind, with relaxed little pauses at the dots",
    },
    "freddie": {
        "voice": "Puck",
        "direction": "You are Freddie, a friendly, chatty little frog in a kids' adventure show. Speak quickly and playfully, "
                     "with a bouncy, croaky charm",
    },
    "tinybugs": {
        "voice": "Leda",
        "direction": "You are five tiny, squeaky, panicky little bugs in a kids' adventure show. Speak fast, high and nervous",
    },
    "megabug": {
        "voice": "Algenib",
        "direction": "You are the Time Eater, an over-the-top cartoon villain in a kids' adventure show: a grumpy, glitchy bug monster. "
                     "Speak in a deep, gravelly, menacing voice, dramatic and theatrical, with evil cackles where it says MWAHAHA. "
                     "Scary in a fun way, never truly frightening",
    },
}

# Free Microsoft Edge neural voices (used with "python make_voices.py edge"), tuned per character.
# Each sentence is acted separately: excited sentences go faster, higher and louder, questions rise,
# trailing "..." slows down, and MEGA-BUG's cackles go extra deep.
EDGE = {
    "chomp":   {"voice": "en-US-BrianNeural",       "rate": 10,  "pitch": 0,   "volume": 5,
                "excited": (12, 6, 15),  "question": (2, 6, 0),  "trail": (-10, -3, 0)},     # energetic, upbeat young man
    "ponder":  {"voice": "en-US-AvaNeural",         "rate": -20, "pitch": -4,  "volume": -10,
                "excited": (4, 3, 0),    "question": (0, 4, 0),  "trail": (-10, -3, -5)},    # slow, soft, calm
    # (the page also plays MEGA-BUG's clips lower and slower, for an extra-deep monster voice)
    "freddie": {"voice": "en-US-GuyNeural",         "rate": 14,  "pitch": 28,  "volume": 0,
                "excited": (8, 8, 10),   "question": (0, 8, 0),  "trail": (-10, -4, -10)},     # quick, croaky, playful
    "tinybugs": {"voice": "en-US-AnaNeural",         "rate": 22,  "pitch": 35,  "volume": 0,
                "excited": (8, 10, 10),  "question": (0, 8, 0),  "trail": (-8, 0, 0)},       # squeaky and panicky
    "megabug": {"voice": "en-US-ChristopherNeural", "rate": 8,   "pitch": -35, "volume": 25,
                "excited": (12, -5, 15), "question": (0, 8, 10), "trail": (-16, -8, 0),
                "cackle": (-18, -20, 45)},                                                    # booming, theatrical villain
}
EDGE_PREFIX = "edge5_"  # bump when the acting changes, so clips are re-recorded

# Lines that live in the page itself (src/quest.html). Keep these exactly in sync with the page.
EXTRA = {
    "chomp": [
        "WHOA, hey! You! Yeah, YOU! You're the hero everyone's been talking about, right?! I NEED your help!",
        "SwampBook is where swamp creatures share what they're building, find teammates, and cheer each other on! Look, here's how it works!",
        "Uh oh... wait. What's going on? Why is the sky getting so dark?!",
        "It's eating EVERYTHING! The whole launch schedule! It's way too much, I can't keep up!",
        "I'll just code FASTER! Type, type, type! Grab the code from the swamp! Take that, Time Eater!",
        "Take THIS!",
        "Snip snip!",
        "YES! The tile clicks in, and the gate rumbles open! You cracked it!",
        "Ooh, so close! Try another one. No rush!",
        "Here's how you do your best work. Does this sound like you?",
        "You skipped everything, and that's totally okay!",
    ],
    "ponder": [
        "Oh... hello there. Sorry, I'm a little slow. I was hoping someone kind would come by.",
        "This is my lily-pad app! It helps everyone at the Pond Fair find their way... the stage, the snacks, and when each demo starts.",
        "Yes... a bottle! It has a neck, but no head. Welcome to the fair, friend.",
        "Hmm... not quite. No rush... try again.",
        "Here's how you do your best work. Does this sound like you?",
        "You skipped everything, and that's totally okay!",
    ],
    "freddie": [
        "Ribbit! And I'm Freddie, Ponder's app buddy! I test every single button so the app is perfect for the fair!",
        "Psst! Ponder! Ribbit! I've got something to tell you about your app!",
        "Ribbit! Step one is my favorite: app updates! Testers are sending bottles, croaks and splashes all at once. Let's sort them out!",
        "My turn! I built the welcome riddle for the app. Ponder, test it on our new friend!",
        "Uh oh... Ponder, the sky looks funny. And the app is starting to flicker...",
        "We did it! The app works! Ponder, the whole pond is lining up at the stage!",
        "There's a bug. The map buttons are swapped. That's it!",
        "Ponder, your app is amazing! Just one teeny thing... the map buttons got swapped. Easy fix!",
        "Psst... just between us... the map buttons are swapped. Nobody else noticed.",
    ],
    "megabug": [
        "Did you REALLY think you could launch SwampBook without facing ME?!",
        "I am the TIME EATER! Born from every GIANT task that nobody EVER broke down!",
        "Mmm... your launch schedule. Deadlines, meetings... ALL of it! Nothing can stop me now!",
        "Your fast typing won't calm down this aggressive schedule. You'll never stop me!",
        "No, no, NOT the scissors! Okay, okay! I surrender! I SURRENDER!",
        "NOOO! Too... much... POWER! You haven't seen the last of MEEEE!",
    ],
    "tinybugs": [
        "Oh no... we're just tiny little tasks now! Easy to finish! Run away!",
    ],
}


def lines_by_speaker():
    out = {name: list(lines) for name, lines in EXTRA.items()}
    for quest in QUESTS.values():
        spoken = out.setdefault(quest["character"], [])
        spoken += [quest["intro"]["line"], quest["finale"]]
        for scene in quest["scenes"]:
            spoken.append(scene["line"])
            spoken += [c["reaction"] for c in scene["choices"]]
    return {name: list(dict.fromkeys(lines)) for name, lines in out.items()}


def clip_name(speaker, text, ext):
    return f"{speaker}_{hashlib.sha1(f'{speaker}|{text}'.encode()).hexdigest()[:12]}.{ext}"


def pick_model(client):
    """The newest Gemini text-to-speech model this key can use (flash preferred: faster)."""
    if MODEL:
        return MODEL
    names = [m.name.split("/")[-1] for m in client.models.list() if "tts" in m.name.lower()]
    if not names:
        sys.exit("This Gemini key has no text-to-speech model. Set GEMINI_TTS_MODEL in .env.")
    names.sort(key=lambda n: ("flash" in n, n), reverse=True)
    return names[0]


def record(client, model, speaker, text):
    from google.genai import types
    s = SPEAKERS[speaker]
    response = client.models.generate_content(
        model=model,
        contents=f"{s['direction']}. Say this line exactly, in character:\n{text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=s["voice"]))
            ),
        ),
    )
    return response.candidates[0].content.parts[0].inline_data.data  # 24 kHz, 16-bit mono PCM


def save(pcm, path_wav):
    with wave.open(str(path_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(pcm)
    if shutil.which("ffmpeg"):  # smaller files when ffmpeg is installed
        mp3 = path_wav.with_suffix(".mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path_wav), "-codec:a", "libmp3lame", "-b:a", "64k", str(mp3)], check=True)
        path_wav.unlink()
        return mp3
    return path_wav


def acted_sentences(speaker, text):
    """Splits a line into sentences, each with its own rate/pitch/volume."""
    import re
    v = EDGE[speaker]
    text = text.replace("*", "")  # stage directions like *blub* are read without the stars
    parts = [p.strip() for p in re.findall(r"[^.!?]+(?:\.\.\.|[.!?]+)?", text) if p.strip()]
    out = []
    for part in parts:
        rate, pitch, volume = v["rate"], v["pitch"], v["volume"]
        if "cackle" in v and re.search(r"MWA|HAHA", part, re.I):
            d = v["cackle"]
        elif part.endswith("!") or re.search(r"\b[A-Z]{3,}\b", part):
            d = v["excited"]
        elif part.endswith("?"):
            d = v["question"]
        elif part.endswith("..."):
            d = v["trail"]
        else:
            d = (0, 0, 0)
        rate, pitch, volume = rate + d[0], pitch + d[1], volume + d[2]
        # ALL-CAPS words are shouted through the acting above, but read as words, not spelled out letter by letter.
        spoken = re.sub(r"\b([A-Z]{2,})\b", lambda m: m.group(1).lower() if m.group(1) not in ("OK",) else m.group(1), part)
        out.append((spoken, f"{rate:+d}%", f"{pitch:+d}Hz", f"{volume:+d}%"))
    return out


def record_edge(speaker, text, path_mp3):
    import asyncio
    import edge_tts

    async def run():
        audio = b""
        for spoken, rate, pitch, volume in acted_sentences(speaker, text):
            async for chunk in edge_tts.Communicate(spoken, EDGE[speaker]["voice"], rate=rate, pitch=pitch, volume=volume).stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
        path_mp3.write_bytes(audio)  # MP3 pieces join cleanly end to end
    asyncio.run(run())


def main():
    engine = "edge" if "edge" in sys.argv[1:] else "gemini"
    if engine == "edge":
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            sys.exit("First run:  pip install edge-tts")
        client = model = None
    else:
        key = env.get("GEMINI_KEY") or env.get("GEMINI_API_KEY")
        if not key:
            sys.exit("Add GEMINI_KEY to .env first.")
        from google import genai
        client = genai.Client(api_key=key)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    todo = [(sp, t) for sp, lines in lines_by_speaker().items() for t in lines]
    if engine == "gemini":
        model = pick_model(client)
    print(f"{len(todo)} lines, {'Edge neural voices' if engine == 'edge' else 'model ' + model}")
    for n, (speaker, text) in enumerate(todo, 1):
        key_ = f"{speaker}|{text}"
        existing = manifest.get(key_)
        # Only keep a clip made by the same engine, so one character never mixes two voices.
        if existing and (OUT / existing).exists() and existing.startswith(EDGE_PREFIX) == (engine == "edge"):
            continue
        if engine == "edge":
            path = OUT / (EDGE_PREFIX + clip_name(speaker, text, "mp3"))
            for attempt in range(3):
                try:
                    record_edge(speaker, text, path)
                    break
                except Exception as e:
                    print(f"  retrying ({str(e)[:100]})")
                    time.sleep(3)
            else:
                print(f"  gave up on: {text[:60]}")
                continue
            if existing and existing != path.name:
                (OUT / existing).unlink(missing_ok=True)
            manifest[key_] = path.name
            manifest["_done"] = [sp for sp in SPEAKERS if all(f"{sp}|{t}" in manifest for s2, t in todo if s2 == sp)]
            manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"[{n}/{len(todo)}] {speaker}: {text[:60]}")
            continue
        for attempt in range(6):
            try:
                pcm = record(client, model, speaker, text)
                break
            except Exception as e:
                msg = str(e)
                if not any(code in msg for code in ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE")):
                    sys.exit(f"Gemini error: {msg[:300]}")
                wait = 20 * (attempt + 1)  # free-tier rate limit: wait and retry
                print(f"  busy, retrying in {wait}s")
                time.sleep(wait)
        else:
            print(f"  gave up on: {text[:60]}")
            continue
        path = save(pcm, OUT / clip_name(speaker, text, "wav"))
        if existing and existing != path.name:
            (OUT / existing).unlink(missing_ok=True)
        manifest[key_] = path.name
        manifest["_done"] = [sp for sp in SPEAKERS if all(f"{sp}|{t}" in manifest for s2, t in todo if s2 == sp)]
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"[{n}/{len(todo)}] {speaker}: {text[:60]}")
    # drop clips for lines that no longer exist
    wanted = {f"{sp}|{t}" for sp, t in todo}
    for k in [k for k in manifest if k not in wanted and not k.startswith("_")]:
        (OUT / manifest.pop(k)).unlink(missing_ok=True)
    # The page only uses a character's Gemini voice once ALL its lines are recorded, so voices never mix.
    manifest["_done"] = [sp for sp in SPEAKERS if all(f"{sp}|{t}" in manifest for s2, t in todo if s2 == sp)]
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Done: {len(manifest) - 1} clips. Characters fully voiced: {', '.join(manifest['_done']) or 'none yet'}")


if __name__ == "__main__":
    main()
