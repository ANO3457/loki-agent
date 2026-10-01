# Mobile Device Matrix & Emulation Reference (`devices.md`)

LOKI provides mobile viewport emulation, touch event dispatching, and responsive layout auditing.

---

## 1. Supported Aliases & Device Presets
LOKI automatically resolves friendly alias names to Playwright's canonical device descriptor catalog:

| Friendly Alias | Resolved Playwright Descriptor | Viewport (Portrait) | Device Scale Factor | Touch Enabled |
| :--- | :--- | :--- | :---: | :---: |
| `iphone` / `iphone-17` | `iPhone 17` | 402 × 681 | 3.0 | Yes |
| `iphone-17-pro` | `iPhone 17 Pro` | 402 × 681 | 3.0 | Yes |
| `iphone-16` | `iPhone 16` | 393 × 659 | 3.0 | Yes |
| `iphone-16-pro` | `iPhone 16 Pro` | 402 × 681 | 3.0 | Yes |
| `iphone-15` | `iPhone 15` | 393 × 659 | 3.0 | Yes |
| `iphone-14` | `iPhone 14` | 390 × 664 | 3.0 | Yes |
| `iphone-se` | `iPhone SE` | 375 × 667 | 2.0 | Yes |
| `pixel` / `pixel-10` | `Pixel 10` | 360 × 732 | 3.0 | Yes |
| `pixel-7` | `Pixel 7` | 412 × 732 | 2.625 | Yes |
| `galaxy` / `galaxy-s24` | `Galaxy S24` | 360 × 780 | 3.0 | Yes |
| `galaxy-z-fold-7` | `Galaxy Z Fold 7` | 984 × 1016 | 2.0 | Yes |
| `galaxy-z-flip-7` | `Galaxy Z Flip 7` | 360 × 764 | 3.0 | Yes |
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
