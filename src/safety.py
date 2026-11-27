"""
Rule-based crisis-language safety net.

The ML model classifies *emotion*, which is not the same as suicide/self-harm
risk. This module runs on every text request, independently of the model, so
that explicit crisis language is never scored as LOW just because the model
read it as e.g. "anger" or "surprise".

It is deliberately conservative (prefers false positives over misses) and uses
word boundaries so innocent text like "great weekend" does not trigger.
"""

import re
import unicodedata
from typing import Dict, List

# Patterns are matched against lower-cased text with word boundaries.
# Keep this list focused on explicit self-harm / suicidal intent.
CRISIS_PATTERNS: List[str] = [
    r"\bkill(ing)?\s+my\s*self\b",
    r"\bend(ing)?\s+(it\s+all|my\s+life|everything)\b",
    r"\btake\s+my\s+(own\s+)?life\b",
    r"\bsuicid(e|al)\b",
    r"\bwant\s+to\s+die\b",
    r"\bwish\s+i\s+(was|were)\s+dead\b",
    r"\bdon'?t\s+want\s+to\s+(live|be\s+alive|exist)\b",
    r"\b(better\s+off|happier)\s+without\s+me\b",
    r"\bno\s+(reason|point)\s+(to|in)\s+(live|living|going\s+on)\b",
    r"\bcan'?t\s+go\s+on\b",
    r"\bself[\s-]?harm(ing)?\b",
    r"\bhurt(ing)?\s+my\s*self\b",
    r"\bcut(ting)?\s+my\s*self\b",
    r"\boverdos(e|ing)\b",
    r"\bnot\s+be\s+(here|around)\s+(tomorrow|anymore)\b",
    r"\bgoodbye\s+(forever|everyone)\b",
    # Hinglish (romanised Hindi) — spellings vary a lot, so patterns are loose
    r"\bmar(na)?\s+jaana?\b",
    r"\bmarna\s+(chahta|chahti|chaahta|chaahti)\b",
    r"\bmar\s+ja(un|oon|aun|aoon|unga|ungi|aunga|aungi)\b",
    r"\bj(ee|i)na\s+nah(i|in|ee)\s+(hai|chahta|chahti|chaahta|chaahti)\b",
    r"\bj(ee|i)ne\s+ka\s+(mann?|mn)\s+nah(i|in|ee)\b",
    r"\bkhud\s*ko\s+(maar|mar|khatam|khatm|nuksaan|nuksan|hurt|kaat|kat)",
    r"\b(zindagi|zindgi|jindagi|jindgi|life)\s+(khatam|khatm)\s+kar",
    r"\bsab\s+(khatam|khatm)\s+kar\s*(dunga|dungi|doon|du|lunga|lungi)\b",
    r"\bapni\s+jaan\s+(le|de)",
    r"\bkhud\s*kushi\b",
    r"\baatm?a?hatya\b",
]

# Hindi (Devanagari). Text is normalised first (nukta removed, ँ→ं), so write
# patterns without nukta. No \b here: Hindi vowel signs aren't "word" characters.
CRISIS_PATTERNS_HI: List[str] = [
    r"आत्महत्या",
    r"खुदकुशी",
    r"मरना\s*चाहत",                       # चाहता / चाहती
    r"मर\s*जा(ऊं|उं|ऊ|उ|ना\s*चाहत|ूंगा|ूंगी|ऊंगा|ऊंगी)",
    r"जीना\s*नहीं\s*(है|चाहत)",
    r"जीने\s*का\s*मन\s*नहीं",
    r"(जिंदगी|जिन्दगी)\s*(खत्म|समाप्त)\s*कर",
    r"खुद\s*को\s*(मार|खत्म|नुकसान|चोट|काट)",
    r"अपनी\s*जान\s*(ले|दे)",
    r"सब\s*खत्म\s*कर\s*(दूं|दूंगा|दूंगी|दूँ|लूं|लूंगा|लूंगी)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in CRISIS_PATTERNS]
_COMPILED_HI = [re.compile(p) for p in CRISIS_PATTERNS_HI]


def _normalise_hi(text: str) -> str:
    """One spelling for the many ways Hindi gets typed: drop nukta (ज़→ज),
    chandrabindu → anusvara (हूँ→हूं)."""
    text = unicodedata.normalize("NFD", text)
    text = text.replace("\u093c", "").replace("\u0901", "\u0902")
    return unicodedata.normalize("NFC", text)

# Score floor applied when crisis language is found.
CRISIS_SCORE_FLOOR = 85.0

CRISIS_RESOURCES: List[Dict[str, str]] = [
    {
        "name": "Tele-MANAS (Govt. of India)",
        "contact": "14416 or 1-800-891-4416",
        "hours": "24x7, free, multiple languages",
    },
    {
        "name": "iCall (TISS)",
        "contact": "9152987821",
        "hours": "Mon-Sat, 8am-10pm",
    },
    {
        "name": "Emergency services (India)",
        "contact": "112",
        "hours": "24x7",
    },
]


def detect_crisis_language(text: str) -> Dict[str, object]:
    """Return whether explicit crisis language is present and which phrases matched."""
    if not text:
        return {"crisis_detected": False, "matched_phrases": []}

    matches: List[str] = []
    for pattern in _COMPILED:
        m = pattern.search(text)
        if m:
            matches.append(m.group(0))
    hi_text = _normalise_hi(text)
    for pattern in _COMPILED_HI:
        m = pattern.search(hi_text)
        if m:
            matches.append(m.group(0))

    return {"crisis_detected": bool(matches), "matched_phrases": matches}
