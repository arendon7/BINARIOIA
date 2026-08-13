from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Any
import json

class BlockKind(str, Enum):
    TITLE = 'title'
    HEADING = 'heading'
    PARAGRAPH = 'paragraph'
    BULLETS = 'bullets'
    NUMBERED = 'numbered'
    TABLE = 'table'
    QUOTE = 'quote'
    CALLOUT = 'callout'
    PAGE_BREAK = 'page_break'

@dataclass
class SourceRef:
    id: str
    title: str
    source_type: str = 'user'
    locator: str = ''
    hash_sha256: str = ''
    notes: str = ''

@dataclass
class ContentBlock:
    id: str
    kind: str
    text: str = ''
    level: int = 1
    items: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class StyleProfile:
    name: str = 'Corporativo'
    font_name: str = 'Aptos'
    body_size_pt: float = 11.0
    heading_color: str = '17365D'
    accent_color: str = '2F75B5'
    title_centered: bool = True
    body_justified: bool = True
    margins_cm: float = 2.5
    line_spacing: float = 1.15
    footer_text: str = 'Binario IA · Documentos IA'
    include_page_numbers: bool = True

@dataclass
class DocumentSpec:
    id: str
    title: str
    document_type: str
    objective: str
    audience: str = ''
    language: str = 'es'
    blocks: list[ContentBlock] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    style: StyleProfile = field(default_factory=StyleProfile)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def save(self, path: str | Path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding='utf-8')

    @classmethod
    def from_json(cls, path: str | Path):
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(
            id=d['id'], title=d['title'], document_type=d['document_type'], objective=d.get('objective',''),
            audience=d.get('audience',''), language=d.get('language','es'),
            blocks=[ContentBlock(**b) for b in d.get('blocks',[])],
            sources=[SourceRef(**s) for s in d.get('sources',[])],
            style=StyleProfile(**d.get('style',{})), metadata=d.get('metadata',{})
        )

@dataclass
class QualityIssue:
    code: str
    severity: str
    message: str
    block_id: Optional[str] = None

@dataclass
class QualityReport:
    score: int
    status: str
    issues: list[QualityIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
