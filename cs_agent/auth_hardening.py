"""Make Google OAuth2 token refresh resilient to transient TLS/connection drops.

Inside Docker Desktop (especially on macOS) the HTTPS call to
``oauth2.googleapis.com/token`` intermittently fails with
``SSL: UNEXPECTED_EOF_WHILE_READING``. google-auth's default transport performs
no retries, so a single dropped handshake fails the whole Gemini request, which
in turn hangs and times out the tau2 task.

Importing this module (before any Gemini/Vertex call) installs a retrying
``requests.Session`` as the default transport used by google-auth when it
refreshes service-account access tokens. It is a no-op if the patch cannot be
applied, so it never makes startup worse.
"""

from __future__ import annotations


def _install() -> None:
    import google.auth.transport.requests as gatr
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.3,  # 0, 0.3, 0.6, 1.2, 2.4s -> ~4.5s worst case
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )

    def _build_session() -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    original_init = gatr.Request.__init__

    def patched_init(self, session=None):  # type: ignore[no-untyped-def]
        if session is None:
            session = _build_session()
        original_init(self, session=session)

    # Idempotent: only patch once.
    if not getattr(gatr.Request, "_auth_hardening_patched", False):
        gatr.Request.__init__ = patched_init  # type: ignore[method-assign]
        gatr.Request._auth_hardening_patched = True  # type: ignore[attr-defined]


try:
    _install()
except Exception:  # pragma: no cover - never block startup on the hardening patch
    pass
