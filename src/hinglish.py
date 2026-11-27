"""
Devanagari (Hindi) → casual romanised Hinglish, e.g.
    "मैं बहुत परेशान हूँ"  →  "main bahut pareshaan hoon"
    "मुझे नींद नहीं आती"   →  "mujhe neend nahin aati"

Rule-based (no extra packages) so it runs anywhere, including Colab on new
Python versions. It follows how people actually type Hindi in chats:
inherent 'a' dropped at word ends and in common middle positions
(करना → karna), long 'aa' at word end written as 'a' (था → tha).
It's an approximation used to create training data, not a perfect transliterator.
"""

import re

CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h",
    # precomposed nukta letters
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y",
}
NUKTA_FORMS = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "य": "y"}
VOWELS = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri",
          "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o"}
MATRAS = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri",
          "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o"}
VIRAMA, NUKTA = "्", "़"
NASAL = {"ं": "n", "ँ": "n"}
VISARGA = "ः"
DIGITS = {chr(0x0966 + i): str(i) for i in range(10)}
PUNCT = {"।": ".", "॥": "."}

_DEV = re.compile(r"[ऀ-ॿ]+")


# Very common words people spell a fixed way in chat
COMMON = {"में": "mein", "हैं": "hain", "मैं": "main", "है": "hai", "हूँ": "hoon", "हूं": "hoon",
          "नहीं": "nahin", "क्या": "kya", "आ": "aa", "जा": "ja", "था": "tha", "थी": "thi"}


def _word(word: str) -> str:
    if word in COMMON:
        return COMMON[word]
    # Split into units: [kind, roman, vowel] where kind is 'c' (consonant) or 'v' (vowel)
    units = []
    i = 0
    while i < len(word):
        ch = word[i]
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch in CONSONANTS:
            roman = CONSONANTS[ch]
            if nxt == NUKTA:
                roman = NUKTA_FORMS.get(ch, roman)
                i += 1
                nxt = word[i + 1] if i + 1 < len(word) else ""
            if nxt in MATRAS:
                units.append(["c", roman, MATRAS[nxt], False])
                i += 2
            elif nxt == VIRAMA:
                units.append(["c", roman, "", False])
                i += 2
            else:
                units.append(["c", roman, "a", True])   # inherent schwa
                i += 1
        elif ch in VOWELS:
            units.append(["v", "", VOWELS[ch], False])
            i += 1
        elif ch in NASAL and units:
            units[-1][2] += NASAL[ch]
            i += 1
        elif ch == VISARGA and units:
            units[-1][2] += "h"
            i += 1
        elif ch in DIGITS:
            units.append(["x", DIGITS[ch], "", False])
            i += 1
        elif ch in PUNCT:
            units.append(["x", PUNCT[ch], "", False])
            i += 1
        else:
            i += 1  # unknown sign: skip

    letters = [u for u in units if u[0] in "cv"]
    # Schwa deletion: word-final, and V C(a) C+matra in the middle (करना → karna)
    for idx, u in enumerate(letters):
        if not u[3]:
            continue
        if idx == len(letters) - 1 and idx > 0:
            u[2] = ""
        elif 0 < idx < len(letters) - 1:
            prev, nxt = letters[idx - 1], letters[idx + 1]
            if prev[2] and nxt[0] == "c" and not nxt[3] and nxt[2]:
                u[2] = ""

    out = "".join(u[1] + u[2] for u in units)
    # Chat-style endings: था → tha, नहीं → nahin, ही → hi
    if len(out) > 3:
        out = re.sub(r"aa$", "a", out)
    out = re.sub(r"een$", "in", out)
    out = re.sub(r"ee$", "i", out)
    return out


def to_hinglish(text: str) -> str:
    """Romanise every Devanagari run; leave English, numbers and punctuation as is."""
    return _DEV.sub(lambda m: _word(m.group(0)), text)


def has_devanagari(text: str) -> bool:
    return bool(_DEV.search(text or ""))


# Common romanised-Hindi words. Deliberately leaves out words that are also
# everyday English ("main", "to", "par", "the", "me", "us", "hi"), so English
# sentences don't get mistaken for Hinglish.
HINGLISH_WORDS = {
    "hai", "hain", "nahi", "nahin", "nhi", "nai", "mujhe", "mujhko", "mera", "meri", "mere",
    "bahut", "bohot", "bhot", "yaar", "yar", "kya", "kyun", "kyu", "kyon", "kuch", "kuchh",
    "aur", "lekin", "hoon", "hu", "tha", "thi", "the", "raha", "rahi", "rahe", "karna", "karta",
    "karti", "karte", "gaya", "gayi", "abhi", "sab", "koi", "bhi", "mein", "toh", "haan",
    "accha", "acha", "achha", "theek", "thik", "zindagi", "zindgi", "pata", "samajh", "lagta",
    "lagti", "dost", "ghar", "kaise", "kaisa", "kab", "kahan", "jab", "agar", "phir", "fir",
    "bas", "bilkul", "matlab", "neend", "dimaag", "pareshaan", "pareshan", "tension", "ho",
    "hota", "hoti", "kar", "ke", "ki", "ka", "ko", "se", "aaj", "kal", "jeena", "marna", "khud",
}
HINGLISH_WORDS -= {"the"}  # 'the' is English; kept out explicitly
_STRONG = {"hai", "hain", "nahi", "nahin", "nhi", "mujhe", "bahut", "bohot", "yaar", "kya", "hoon",
           "kuch", "kuchh", "raha", "rahi", "mein", "toh", "accha", "acha", "theek", "zindagi", "kaise"}


def detect_language(text: str) -> str:
    """'hi' (Devanagari), 'hinglish' (romanised Hindi, often mixed with English) or 'en'."""
    if has_devanagari(text):
        return "hi"
    words = re.findall(r"[a-z]+", (text or "").lower())
    if not words:
        return "en"
    hits = [w for w in words if w in HINGLISH_WORDS]
    strong = [w for w in hits if w in _STRONG]
    if strong and (len(hits) >= 2 or len(words) <= 4) and len(hits) / len(words) >= 0.15:
        return "hinglish"
    return "en"
