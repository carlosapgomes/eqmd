# Phase 4: Element Web + Well-Known

## Goals
- Serve Element Web at `https://${CHAT_FQDN}`
- Publish `/.well-known/matrix/client` on `https://${MATRIX_FQDN}`
- Provide a clean UX (no VoIP UI, no integrations, minimal settings)

## Element Web Configuration
Element Web reads `element/config.json` (generated from `element/config.json.template`).
Key defaults in the template:
- Single homeserver: `${MATRIX_PUBLIC_BASEURL}` / `${MATRIX_FQDN}`
- VoIP UI disabled via `setting_defaults.UIFeature.voip = false`
- Integrations disabled (`integrations_*` empty)
- Custom CSS at `/custom.css` for hiding room creation UI

To regenerate configs after editing templates:
```bash
uv run python scripts/generate_matrix_configs.py
```

## Well-Known Client
Served from the Matrix domain:
`https://${MATRIX_FQDN}/.well-known/matrix/client`

Current JSON response (from `nginx/matrix.conf`):
```json
{
  "m.homeserver": { "base_url": "https://${MATRIX_FQDN}/" },
  "io.element.e2ee": { "default": false, "force_disable": true },
  "m.identity_server": { "base_url": "" }
}
```

Note: this is a client hint only. Server-side enforcement is handled in Phase 5.

## Nginx
- `nginx/matrix.conf` serves the Matrix client API and the well-known client JSON.
- `nginx/element.conf` proxies `https://${CHAT_FQDN}` to the Element Web container.

## Custom CSS
`element/custom.css` is mounted into the Element Web container and loaded via `custom_css_url`.
If you adjust selectors, regenerate the container by restarting `element-web`.

## Mobile Client Onboarding (Element)
1. Install Element on iOS or Android.
2. When asked for the homeserver, enter `${MATRIX_FQDN}`.
3. Tap "Login with SSO" and authenticate using EquipeMed credentials.
4. Confirm you can sync and see your rooms.

If room creation still appears in the UI, hide it with custom CSS or wait for Phase 5 enforcement.
