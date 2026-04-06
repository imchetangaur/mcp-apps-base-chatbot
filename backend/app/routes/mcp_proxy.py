"""MCP Proxy — serves MCP app HTML content in a sandboxed iframe.
Follows the Goose pattern: mcp_app_proxy.rs + mcp_app_proxy.html
"""

import uuid
import time

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.services.mcp_manager import mcp_manager

router = APIRouter(prefix="/api/mcp-proxy", tags=["mcp-proxy"])

# In-memory store for guest HTML (nonce → html, TTL 5 min, max 64 entries)
_guest_html_store: dict[str, dict] = {}
_MAX_STORE_SIZE = 64
_TTL_SECONDS = 300


def _cleanup_store():
    """Remove expired entries."""
    now = time.time()
    expired = [k for k, v in _guest_html_store.items() if now - v["created"] > _TTL_SECONDS]
    for k in expired:
        _guest_html_store.pop(k, None)


@router.get("/sandbox", response_class=HTMLResponse)
async def mcp_app_proxy():
    """
    Returns the sandbox proxy HTML page.
    This is loaded as the outer iframe — it creates a guest iframe
    inside it and relays postMessage between host (React) and guest (MCP app).
    """
    return HTMLResponse(content=SANDBOX_PROXY_HTML, headers={
        "Content-Security-Policy": (
            "default-src 'none'; "
            "script-src 'unsafe-inline'; "
            "style-src 'unsafe-inline'; "
            "frame-src blob: data: http: https:; "
            "img-src * data: blob:; "
            "connect-src *; "
            "font-src * data:; "
            "media-src * data: blob:;"
        ),
        "Cache-Control": "no-cache",
    })


@router.post("/guest")
async def store_guest_html(request: Request):
    """Store guest HTML and return a nonce for retrieval (one-time use)."""
    _cleanup_store()

    # Evict oldest if at capacity
    if len(_guest_html_store) >= _MAX_STORE_SIZE:
        oldest_key = min(_guest_html_store, key=lambda k: _guest_html_store[k]["created"])
        _guest_html_store.pop(oldest_key)

    body = await request.json()
    html = body.get("html", "")
    nonce = str(uuid.uuid4())
    _guest_html_store[nonce] = {"html": html, "created": time.time()}
    return JSONResponse({"nonce": nonce})


@router.get("/guest", response_class=HTMLResponse)
async def serve_guest_html(nonce: str = Query(...)):
    """Serve stored guest HTML (one-time use, consumed on read)."""
    entry = _guest_html_store.pop(nonce, None)
    if not entry:
        raise HTTPException(status_code=404, detail="Guest HTML not found or already consumed")

    return HTMLResponse(content=entry["html"], headers={
        "Content-Security-Policy": (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http:; "
            "style-src 'self' 'unsafe-inline' https: http:; "
            "img-src * data: blob:; "
            "font-src * data:; "
            "connect-src *; "
            "frame-src blob: data: https: http:; "
            "media-src * data: blob:;"
        ),
        "Referrer-Policy": "strict-origin",
        "Cache-Control": "no-store",
    })


@router.post("/read-resource")
async def read_resource(request: Request):
    """Read a resource from an MCP server."""
    body = await request.json()
    session_id = body.get("session_id")
    extension_name = body.get("extension_name")
    uri = body.get("uri")

    if not all([session_id, extension_name, uri]):
        raise HTTPException(status_code=400, detail="Missing session_id, extension_name, or uri")

    try:
        result = await mcp_manager.read_resource(session_id, extension_name, uri)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# The sandbox proxy HTML template
# Following Goose's mcp_app_proxy.html pattern:
# - Outer iframe receives HTML from host (React) via postMessage
# - Stores HTML server-side, loads guest iframe from real URL
# - Relays messages bidirectionally between host and guest
SANDBOX_PROXY_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
  iframe {
    width: 100%; height: 100%; border: none;
    position: absolute; top: 0; left: 0;
  }
</style>
</head>
<body>
<script>
(function() {
  var guestIframe = null;
  var baseUrl = window.location.origin;

  // Listen for messages from Host (React app)
  window.addEventListener('message', function(event) {
    var data = event.data;
    if (!data || typeof data !== 'object') return;

    // Host sends 'load-html' to load content into sandbox
    if (data.type === 'load-html') {
      loadGuestHtml(data.html, data.css);
      return;
    }

    // Forward other messages from Host to Guest
    if (guestIframe && guestIframe.contentWindow) {
      guestIframe.contentWindow.postMessage(data, '*');
    }
  });

  async function loadGuestHtml(html, css) {
    // Remove existing guest iframe
    if (guestIframe) {
      guestIframe.remove();
      guestIframe = null;
    }

    // Wrap HTML with full document structure if needed
    var fullHtml = html;
    if (!html.toLowerCase().includes('<html')) {
      fullHtml = '<!DOCTYPE html><html><head>' +
        '<meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<style>* { box-sizing: border-box; } body { margin: 0; font-family: -apple-system, sans-serif; }</style>' +
        (css ? '<style>' + css + '</style>' : '') +
        '</head><body>' + html + '</body></html>';
    }

    // Inject resize observer script to communicate height to parent
    var resizeScript = '<script>' +
      'new ResizeObserver(function(entries) {' +
        'var h = document.documentElement.scrollHeight;' +
        'window.parent.postMessage({type:"resize",height:h}, "*");' +
      '}).observe(document.documentElement);' +
      // Relay messages from guest content to host
      'window.addEventListener("message", function(e) {' +
        'if (e.source !== window) window.parent.postMessage(e.data, "*");' +
      '});' +
      '<\\/script>';

    fullHtml = fullHtml.replace('</body>', resizeScript + '</body>');

    try {
      // Store HTML server-side and get a nonce URL (Goose pattern)
      var resp = await fetch(baseUrl + '/api/mcp-proxy/guest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html: fullHtml })
      });
      var result = await resp.json();

      guestIframe = document.createElement('iframe');
      guestIframe.setAttribute('sandbox',
        'allow-scripts allow-same-origin allow-forms allow-popups allow-modals');
      guestIframe.src = baseUrl + '/api/mcp-proxy/guest?nonce=' + result.nonce;
      document.body.appendChild(guestIframe);

      // Listen for messages from guest iframe
      window.addEventListener('message', function guestListener(e) {
        if (guestIframe && e.source === guestIframe.contentWindow) {
          // Forward guest messages to host (React)
          window.parent.postMessage(e.data, '*');
        }
      });
    } catch (err) {
      // Fallback: use srcdoc if server storage fails
      guestIframe = document.createElement('iframe');
      guestIframe.setAttribute('sandbox',
        'allow-scripts allow-same-origin allow-forms allow-popups');
      guestIframe.srcdoc = fullHtml;
      document.body.appendChild(guestIframe);
    }
  }

  // Notify host that sandbox is ready
  window.parent.postMessage({ type: 'sandbox-ready' }, '*');
})();
</script>
</body>
</html>
"""
