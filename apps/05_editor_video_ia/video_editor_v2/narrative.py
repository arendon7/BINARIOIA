from __future__ import annotations
import re, unicodedata
from collections import Counter
from dataclasses import replace
from typing import Protocol
from .models import TranscriptSegment

STOPWORDS = {"de","la","el","y","en","que","a","los","las","un","una","por","para","con","del","es","se","lo","como","al","su","o","pero","más","ya","esto","esta","este","yo","tu","nos","mi","si","porque","cuando","the","and","of","to","in","is","it","for","with","that","this"}

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", text)

def keywords(text: str, limit: int = 8) -> list[str]:
    tokens = [t for t in normalize(text).split() if len(t) >= 3 and t not in STOPWORDS]
    return [w for w, _ in Counter(tokens).most_common(limit)]

class NarrativeProvider(Protocol):
    def analyze(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]: ...

class HeuristicNarrativeAnalyzer:
    HOOK = ("sabias", "imagina", "quieres", "problema", "te ha pasado", "hoy", "mira")
    CTA = ("contact", "escribe", "visita", "comenta", "compra", "agenda", "llama", "sigu")
    CLOSE = ("gracias", "en resumen", "para terminar", "finalmente", "con esto")
    EXAMPLE = ("por ejemplo", "ejemplo", "imagina que", "supongamos")
    EVIDENCE = ("datos", "estudio", "resultado", "demuestra", "por ciento")
    ARGUMENT = ("porque", "por eso", "razon", "debido", "significa")

    def analyze(self, segments):
        seen, out, n = [], [], len(segments)
        for i, seg in enumerate(segments):
            txt = normalize(seg.text)
            role = seg.role if seg.role != "other" else self._role(txt, i, n)
            kws = keywords(seg.text)
            redundancy = seg.redundancy
            if seen and kws:
                redundancy = max(redundancy, max(self._j(set(kws), set(prev)) for prev in seen[-8:]))
            seen.append(kws)
            out.append(replace(seg, role=role, keywords=kws, redundancy=redundancy,
                               relevance=min(1.0, max(seg.relevance, .55 + min(len(kws),7)*.035)),
                               clarity=min(1.0, max(seg.clarity, .64 if 3 <= len(seg.text.split()) <= 35 else .56)),
                               energy=min(1.0, max(seg.energy, .60 if "!" in seg.text or "?" in seg.text else .5))))
        return out

    def _role(self, txt, i, n):
        if any(c in txt for c in self.CTA): return "cta"
        if any(c in txt for c in self.CLOSE) or (i == n-1 and n > 2): return "closing"
        if any(c in txt for c in self.EXAMPLE): return "example"
        if any(c in txt for c in self.EVIDENCE): return "evidence"
        if any(c in txt for c in self.ARGUMENT): return "argument"
        if i == 0 or (i <= 1 and any(c in txt for c in self.HOOK)): return "hook"
        if i <= max(1,n//5): return "context"
        if i <= max(2,n//2): return "main_idea"
        return "other"

    @staticmethod
    def _j(a,b): return len(a & b)/max(1,len(a | b)) if a and b else 0.0

class CallbackNarrativeAnalyzer:
    def __init__(self, callback): self.callback = callback
    def analyze(self, segments):
        payload = [{"id":s.id,"text":s.text,"start":s.start,"end":s.end,"source_id":s.source_id} for s in segments]
        updates = {x["id"]:x for x in self.callback(payload)}
        out=[]
        for s in segments:
            u=updates.get(s.id,{})
            out.append(replace(s, role=u.get("role",s.role), relevance=float(u.get("relevance",s.relevance)), clarity=float(u.get("clarity",s.clarity)), energy=float(u.get("energy",s.energy)), redundancy=float(u.get("redundancy",s.redundancy)), must_keep=bool(u.get("must_keep",s.must_keep)), keywords=list(u.get("keywords",s.keywords or keywords(s.text))), narrative_order=u.get("narrative_order",s.narrative_order)))
        return out
