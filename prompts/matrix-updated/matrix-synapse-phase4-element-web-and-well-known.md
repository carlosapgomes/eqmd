# Phase 4: Element Web + Well-Known + Client UX Defaults

## Goal
Deliver a usable client experience on:
- Element Web at `https://${CHAT_FQDN}`
- Element mobile (using `${MATRIX_FQDN}` homeserver)

While enforcing policy server-side (Phase 5), we also tune defaults to match your constraints:
- no VoIP/video UI
- no E2EE by default
- no user room creation UI (best-effort UX only)

## 1) Element Web config (`element/config.json`)
Configure:
- `default_server_config.m.homeserver.base_url = "https://${MATRIX_FQDN}"`
- disable integrations
- disable VoIP UI features
- set Brazilian defaults (optional)

Important: UI toggles are **not enforcement**. They reduce confusion, but Phase 5 must block server-side.

## 2) `.well-known/matrix/client`
Serve on `https://${MATRIX_FQDN}/.well-known/matrix/client` (recommended).

Include:
- homeserver base URL
- Element E2EE hint (supported by Element clients; behavior varies by version)

Example skeleton:
```json
{
  "m.homeserver": { "base_url": "https://${MATRIX_FQDN}" },
  "io.element.e2ee": { "default": false }
}
```

If you choose to “force disable” E2EE, only do so after verifying both Element Web and mobile honor it for your chosen versions.

## 3) Nginx for Element Web
- Proxy `/` to `http://127.0.0.1:8080`
- Ensure CSP and caching are compatible with Element

## 4) Mobile client onboarding
Document the login steps for staff:
- enter homeserver: `${MATRIX_FQDN}`
- use “Login with SSO”
- authenticate with EquipeMed credentials

## Exit Criteria
- `https://${CHAT_FQDN}` loads Element Web and points at your homeserver
- Element mobile can log in via SSO and sync
- Users cannot find “create room” UX easily (but enforcement is still Phase 5)
