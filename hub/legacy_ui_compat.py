from __future__ import annotations

from urllib.parse import unquote, urlparse

LEGACY_PAGES = {
    "/workspace-detail": "workspace_detail.html",
    "/decision-center": "decision_center.html",
    "/project-intelligence": "project_intelligence.html",
    "/project-memory": "project_memory.html",
    "/workspace-inspector": "workspace_inspector.html",
    "/context-lineage": "context_lineage.html",
    "/impact": "impact_analysis.html",
}


def install(handler_cls, root):
    original_get = handler_cls.do_GET

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        page = LEGACY_PAGES.get(path)
        if page:
            return self._file(root / "hub" / "ui" / page)
        return original_get(self)

    handler_cls.do_GET = do_GET
    return handler_cls
