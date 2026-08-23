---
name: Canvas iframe WebSocket protocol
description: After every IMBRA system update, mandatory checklist to avoid stuck "Running" state in the Canvas iframe.
---

## Rule
After EVERY workflow restart or code change that triggers a rerun, always execute these two steps as the FINAL action before handing back to the user:

1. `restart_workflow("IMBRA Chamada (main.py)")` — wait for RUNNING status
2. `applyCanvasActions` — update shape `artifact:v3:default-imbra-chamada-main-py` with a cache-busted URL

## Why
The Replit Canvas iframe uses a different WebSocket proxy path than the standard Preview pane. After a server restart, this proxy layer sometimes gets permanently stuck with WebSocket onerror floods even though `curl localhost:5000/_stcore/health` returns "ok". Force-reloading the iframe shape via `applyCanvasActions` breaks the stuck state.

Never append `:5000` to the public `replit.dev` URL. Port 5000 is internal; the public preview is served at the domain root after Replit forwards it to external port 80. A public URL ending in `:5000` returns the Replit “couldn't reach this app” page even while Streamlit is healthy.

## URL format for reload
Direct Streamlit URL (bypasses workspace_iframe.html wrapper, more stable):
`https://${REPLIT_DEV_DOMAIN}/?_r=<unique-cache-token>`

Current domain: `8859dbcc-e36e-4d16-8217-c288d14b7b73-00-3ce8mxj6fzww0.riker.replit.dev`
Shape ID: `artifact:v3:default-imbra-chamada-main-py`

## How to apply
Run at the END of every update session, without waiting for the user to ask:
```javascript
await applyCanvasActions({
  actions: [{
    type: "update",
    shapeId: "artifact:v3:default-imbra-chamada-main-py",
    updates: {
      shapeType: "iframe",
      url: "https://8859dbcc-e36e-4d16-8217-c288d14b7b73-00-3ce8mxj6fzww0.riker.replit.dev/?_r=<unique-cache-token>",
      state: "live"
    }
  }]
});
```

## If still stuck after reload
The Canvas iframe session is permanently broken for that browser session. Only fix: user refreshes the browser tab (Ctrl+R / Cmd+R) on the Canvas page. The standard Preview pane is always stable and recommended for day-to-day use.
