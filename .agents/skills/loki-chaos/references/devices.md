# Mobile Device Matrix & Emulation Reference (`devices.md`)

LOKI provides mobile viewport emulation, touch event dispatching, and responsive layout auditing.

---

## 1. Supported Aliases & Device Presets
LOKI automatically resolves friendly alias names to Playwright's canonical device descriptor catalog:

| Friendly Alias | Resolved Playwright Descriptor | Viewport (Portrait) | Device Scale Factor | Touch Enabled |
| :--- | :--- | :--- | :---: | :---: |
| `iphone-15` / `iphone` | `iPhone 15` | 393 × 659 | 3.0 | Yes |
| `iphone-14` | `iPhone 14` | 390 × 664 | 3.0 | Yes |
| `iphone-se` | `iPhone SE` | 375 × 667 | 2.0 | Yes |
| `pixel-7` / `pixel` | `Pixel 7` | 412 × 732 | 2.625 | Yes |
| `galaxy-s24` | `Galaxy S24` | 412 × 915 | 3.0 | Yes |
| `ipad-pro-11` / `ipad` | `iPad Pro 11` | 834 × 1194 | 2.0 | Yes |

*Note:* You can pass any device name from Playwright's built-in catalog (e.g. `'Desktop Chrome'`, `'Pixel 5'`).

---

## 2. Screen Orientation
- `--orientation portrait` (default): Standard vertical handheld orientation.
- `--orientation landscape`: Rotates viewport dimensions by appending `' landscape'` to the Playwright descriptor name (e.g. `iPhone 15 landscape`).

---

## 3. Responsive Layout Sniffing
During mobile sessions, `ChaosSandbox` runs an in-page layout audit:
1. **Horizontal Scroll Overflow**: Compares `document.documentElement.scrollWidth` against `viewport.width`. If content width exceeds the viewport width by > 5px, it flags an unhandled overflow bug with exact pixel measurements.
2. **Viewport Meta Tag Audit**: Checks for presence of `<meta name="viewport">` and verifies that it contains the `width=device-width` directive.
