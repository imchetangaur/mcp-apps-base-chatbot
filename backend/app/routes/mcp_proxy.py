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


@router.get("/mcp-apps-sandbox", response_class=HTMLResponse)
async def mcp_apps_sandbox():
    """MCP Apps sandbox proxy — speaks JSON-RPC protocol for @mcp-ui/client AppRenderer."""
    return HTMLResponse(content=MCP_APPS_SANDBOX_HTML, headers={
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


@router.get("/sandbox", response_class=HTMLResponse)
async def mcp_app_proxy():
    """Legacy sandbox proxy (load-html protocol)."""
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


# The sandbox proxy HTML template (legacy — load-html protocol)
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

  window.addEventListener('message', function(event) {
    var data = event.data;
    if (!data || typeof data !== 'object') return;

    if (data.type === 'load-html') {
      loadGuestHtml(data.html, data.css);
      return;
    }

    if (guestIframe && guestIframe.contentWindow) {
      guestIframe.contentWindow.postMessage(data, '*');
    }
  });

  async function loadGuestHtml(html, css) {
    if (guestIframe) {
      guestIframe.remove();
      guestIframe = null;
    }

    var fullHtml = html;
    if (!html.toLowerCase().includes('<html')) {
      fullHtml = '<!DOCTYPE html><html><head>' +
        '<meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<style>* { box-sizing: border-box; } body { margin: 0; font-family: -apple-system, sans-serif; }</style>' +
        (css ? '<style>' + css + '</style>' : '') +
        '</head><body>' + html + '</body></html>';
    }

    var resizeScript = '<script>' +
      'new ResizeObserver(function(entries) {' +
        'var h = document.documentElement.scrollHeight;' +
        'window.parent.postMessage({type:"resize",height:h}, "*");' +
      '}).observe(document.documentElement);' +
      'window.addEventListener("message", function(e) {' +
        'if (e.source !== window) window.parent.postMessage(e.data, "*");' +
      '});' +
      '<\\/script>';

    fullHtml = fullHtml.replace('</body>', resizeScript + '</body>');

    try {
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

      window.addEventListener('message', function guestListener(e) {
        if (guestIframe && e.source === guestIframe.contentWindow) {
          window.parent.postMessage(e.data, '*');
        }
      });
    } catch (err) {
      guestIframe = document.createElement('iframe');
      guestIframe.setAttribute('sandbox',
        'allow-scripts allow-same-origin allow-forms allow-popups');
      guestIframe.srcdoc = fullHtml;
      document.body.appendChild(guestIframe);
    }
  }

  window.parent.postMessage({ type: 'sandbox-ready' }, '*');
})();
</script>
</body>
</html>
"""


# MCP Apps sandbox proxy — speaks JSON-RPC protocol for @mcp-ui/client AppRenderer
# Handles theme switching via ui/notifications/host-context-changed
MCP_APPS_SANDBOX_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
  iframe { width: 100%; height: 100%; border: none; position: absolute; top: 0; left: 0; }
</style>
</head>
<body>
<script>
(function() {
  var guestIframe = null;

  var DARK_THEME = {
    '--bg-primary':'#151515','--text-primary':'#ffffff',
    '--bg-secondary':'#1f1f1f','--text-secondary':'#c7c7c7',
    '--bg-surface':'#292929','--text-muted':'#707070',
    '--accent':'#92c5f9','--accent-hover':'#b9dafc',
    '--border':'#383838','--border-subtle':'#2a2a2a',
    '--success':'#87bb62','--error':'#f0561d',
    '--radius':'8px','--radius-lg':'12px'
  };

  var LIGHT_THEME = {
    '--bg-primary':'#ffffff','--text-primary':'#1a1a1a',
    '--bg-secondary':'#f5f5f5','--text-secondary':'#4a4a4a',
    '--bg-surface':'#e8e8e8','--text-muted':'#8a8a8a',
    '--accent':'#2563eb','--accent-hover':'#1d4ed8',
    '--border':'#d4d4d4','--border-subtle':'#e5e5e5',
    '--success':'#16a34a','--error':'#dc2626',
    '--radius':'8px','--radius-lg':'12px'
  };

  var currentTheme = 'dark';

  function buildThemeCSS(vars) {
    var css = ':root{';
    for (var k in vars) css += k + ':' + vars[k] + ';';
    css += '}body{background:var(--bg-primary);color:var(--text-primary);' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;' +
      'margin:0;padding:16px;}';
    return css;
  }

  function getThemeVars(theme) {
    return theme === 'light' ? LIGHT_THEME : DARK_THEME;
  }

  // Map MCP Apps standard variables to our custom variables
  function mapHostStyles(hostVars) {
    var mapped = {};
    var mapping = {
      '--color-background-primary': '--bg-primary',
      '--color-background-secondary': '--bg-secondary',
      '--color-background-tertiary': '--bg-surface',
      '--color-text-primary': '--text-primary',
      '--color-text-secondary': '--text-secondary',
      '--color-text-tertiary': '--text-muted',
      '--color-border-primary': '--border',
      '--color-border-secondary': '--border-subtle'
    };
    for (var stdKey in hostVars) {
      if (mapping[stdKey]) {
        mapped[mapping[stdKey]] = hostVars[stdKey];
      }
      mapped[stdKey] = hostVars[stdKey];
    }
    return mapped;
  }

  // Apply theme change to the guest iframe
  function applyThemeToGuest(theme, hostStyles) {
    if (!guestIframe || !guestIframe.contentWindow) return;
    currentTheme = theme || currentTheme;
    var vars = getThemeVars(currentTheme);
    if (hostStyles && hostStyles.variables) {
      var mapped = mapHostStyles(hostStyles.variables);
      for (var k in mapped) vars[k] = mapped[k];
    }
    // Send theme update to guest iframe
    guestIframe.contentWindow.postMessage({
      type: '__mcp_theme_update',
      theme: currentTheme,
      variables: vars
    }, '*');
  }

  window.addEventListener('message', function(event) {
    var data = event.data;
    if (!data || typeof data !== 'object') return;

    if (data.jsonrpc === '2.0' && data.method === 'ui/notifications/sandbox-resource-ready') {
      loadGuestHtml(data.params.html, data.params.sandbox);
      return;
    }

    // Handle theme changes from host
    if (data.jsonrpc === '2.0' && data.method === 'ui/notifications/host-context-changed') {
      applyThemeToGuest(data.params.theme, data.params.styles);
      // Also forward to guest for apps using the MCP Apps SDK directly
      if (guestIframe && guestIframe.contentWindow) {
        guestIframe.contentWindow.postMessage(data, '*');
      }
      return;
    }

    if (data.jsonrpc === '2.0' && guestIframe && guestIframe.contentWindow) {
      guestIframe.contentWindow.postMessage(data, '*');
    }
  });

  function loadGuestHtml(html, sandboxAttr) {
    if (guestIframe) {
      guestIframe.remove();
      guestIframe = null;
    }

    var themeCSS = buildThemeCSS(getThemeVars(currentTheme));

    var fullHtml = html;
    if (!html.toLowerCase().includes('<html')) {
      fullHtml = '<!DOCTYPE html><html><head>' +
        '<meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<style id="__mcp_theme">' + themeCSS + '</style>' +
        '</head><body>' + html + '</body></html>';
    } else if (!html.includes('id="__mcp_theme"')) {
      fullHtml = fullHtml.replace('<head>', '<head><style id="__mcp_theme">' + themeCSS + '</style>');
    }

    var injectedScript = '<script>' +
      // mcpAction helper for interactivity
      'function mcpAction(text){' +
        'window.parent.postMessage({' +
          'jsonrpc:"2.0",id:"action-"+Date.now()+"-"+Math.random(),' +
          'method:"ui/message",' +
          'params:{content:[{type:"text",text:text}]}' +
        '},"*");' +
      '}' +
      // Listen for theme updates from sandbox proxy
      'window.addEventListener("message",function(e){' +
        'var d=e.data;' +
        'if(d&&d.type==="__mcp_theme_update"&&d.variables){' +
          'var root=document.documentElement;' +
          // Suppress transitions during theme switch
          'var s=document.getElementById("__mcp_no_transition");' +
          'if(!s){s=document.createElement("style");s.id="__mcp_no_transition";document.head.appendChild(s);}' +
          's.textContent="*,*::before,*::after{transition:none!important}";' +
          'for(var k in d.variables)root.style.setProperty(k,d.variables[k]);' +
          'root.setAttribute("data-theme",d.theme||"dark");' +
          'document.documentElement.style.colorScheme=d.theme||"dark";' +
          // Re-enable transitions after repaint
          'requestAnimationFrame(function(){requestAnimationFrame(function(){s.textContent="";});});' +
        '}' +
        // Relay other messages to sandbox proxy -> host
        'if(e.source!==window)window.parent.postMessage(d,"*");' +
      '});' +
      // ResizeObserver
      'new ResizeObserver(function(){' +
        'var h=document.documentElement.scrollHeight;' +
        'window.parent.postMessage({' +
          'jsonrpc:"2.0",' +
          'method:"ui/notifications/size-changed",' +
          'params:{height:h}' +
        '},"*");' +
      '}).observe(document.documentElement);' +
      // Initialized notification
      'setTimeout(function(){' +
        'window.parent.postMessage({' +
          'jsonrpc:"2.0",' +
          'method:"ui/notifications/initialized",' +
          'params:{}' +
        '},"*");' +
      '},50);' +
      '<\\/script>';

    fullHtml = fullHtml.replace('</body>', injectedScript + '</body>');

    guestIframe = document.createElement('iframe');
    guestIframe.setAttribute('sandbox',
      sandboxAttr || 'allow-scripts allow-same-origin allow-forms allow-popups allow-modals');
    guestIframe.srcdoc = fullHtml;
    document.body.appendChild(guestIframe);

    window.addEventListener('message', function(e) {
      if (guestIframe && e.source === guestIframe.contentWindow) {
        window.parent.postMessage(e.data, '*');
      }
    });
  }

  window.parent.postMessage({
    jsonrpc: '2.0',
    method: 'ui/notifications/sandbox-proxy-ready',
    params: {}
  }, '*');
})();
</script>
</body>
</html>
"""
