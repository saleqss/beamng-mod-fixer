# 🚗 BeamNG.drive Mod Headlight Fixer & Graphics Optimizer (`agy-beam`)

[![CI](https://github.com/saleqss/beamng-mod-fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/saleqss/beamng-mod-fixer/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-197%20passed-brightgreen)](https://github.com/saleqss/beamng-mod-fixer)

> **The definitive utility to repair broken or pitch-black headlights in BeamNG.drive vehicle mods with 100% precision, preserve highbeam environmental shadows without cockpit light bleed, optimize graphics settings for maximum FPS, and clean shader caches.**

*Читать на русском языке: [README_RU.md](README_RU.md)*

---

## ⚡ Install with One Command via Git

You can install `beamng-mod-fixer` directly from GitHub using pip:

```bash
pip install git+https://github.com/saleqss/beamng-mod-fixer.git
```

Once installed, open any terminal (PowerShell, Command Prompt, or Bash) and simply type:

```bash
agy-beam
```

*(or `beamng-mod-fixer`)*

---

## 🔍 The Root Cause: Why Did Previous Fixers Break Working Lights?

Many players noticed that after using previous scripts or blunt replacements:
- **Mods where headlights worked stopped working properly** (cockpit blinded by light bleed, highbeams lost depth).
- **Mods with broken headlights did not get fixed at all**.

### 1. The Lowbeam vs Highbeam Problem
- In modern BeamNG (Torque3D Clustered Forward+ PBR), vanilla vehicles intentionally use `"lightCastShadows": false` for **lowbeams** (to avoid front bumper self-shadow occlusion and save GPU draw-calls) and `"lightCastShadows": true` for **highbeams**.
- If a script bluntly sets `lightCastShadows: false` everywhere:
  - **Highbeam shadows disappear**, causing light to bleed through the firewall and dashboard directly into the driver's cockpit view, blinding the player at night.
  - Working vehicles lose their realistic distance shadows.

### 2. Why Broken Lights Did Not Turn On
A light with `lightCastShadows: false` will still fail to illuminate if:
- **Obsolete Cookie Path**: Pre-PBR paths like `art/shapes/lights/headlight_cookie.dds` were removed in BeamNG 0.24+. When Torque3D fails to load the cookie texture, it throws a 404 texture error and disables the spotlight entirely.
- **Legacy Flare Names**: Using `flareName: "none"` or deprecated flare names like `headlightFlare` instead of `vehicleHeadLightFlare`.
- **Inverted Spotlight Angles**: Mods with `lightInnerAngle > lightOuterAngle` cause a mathematical division error in Torque3D cone falloff, resulting in 0 light intensity.
- **Misspelled Electrics**: Spotlight rows using `low_beam` or `high_beam` instead of standard `lowbeam` or `highbeam`.
- **Disabled Deferred Lighting**: If graphics settings disable `deferredLighting`, dynamic forward+ lights are culled across the entire game engine!

---

## ✨ Features & Smart Selective Fix Engine

- 🧠 **Smart Selective Headlight Fix (Default)**:
  - **Lowbeam & Fog Lights**: Changes `lightCastShadows: true` to `false` (eliminates bumper self-shadow blackout).
  - **Highbeam Lights**: Strictly PRESERVES `lightCastShadows: true` (prevents cockpit blinding and maintains environmental shadows).
  - **Cookie Modernization**: Automatically converts legacy `art/shapes/lights/*` to official modern `art/special/BNG_light_cookie_headlight.dds`.
  - **Flare Modernization**: Replaces deprecated `headlightFlare` / `highbeamFlare` with `vehicleHeadLightFlare` / `vehicleHighBeamFlare`.
  - **Angle Repair**: Automatically repairs inverted cone angles (`inner > outer`).
  - **Electrics Normalization**: Corrects non-standard electrics signal names (`low_beam` -> `lowbeam`).
- ⚡ **Atomic In-Place Processing**: Modifies `.zip` archives via streaming swap buffers. Zero disk bloat, preserves UTF-8 filenames, textures, meshes, and folder structures.
- 🚀 **Graphics Optimizer**: Deploys balanced high-FPS settings (`facesPerUpdate: 2`, `textureSize: 512`, `deferredLighting: true`, `maxLights: 32`) with automatic timestamped `.bak` backups.
- 🧹 **Shader Cache Cleaner**: Safely purges DirectX/Vulkan shader cache binaries (`.d3dcsx`, `.db`) in `temp/` without touching user configs (`.pc`).
- 🧪 **197 Automated Tests**: 100% test coverage across feature, boundary, atomic rewrite, and adversarial tiers.

---

## 🚀 Interactive Usage

Simply run:

```bash
agy-beam
```

```text
======================================================================
              Mod Headlight Fixer & Graphics Optimizer v1.0.0
======================================================================

Detected BeamNG User Directory: C:\Users\user\AppData\Local\BeamNG\BeamNG.drive\current

Select an action to perform:
  1) Smart Fix broken headlights in all mods (recommended, preserves highbeams)
  2) Legacy Fix broken headlights (force lightCastShadows: false everywhere)
  3) Optimize graphics settings (high FPS + crisp visuals)
  4) Clean shader and texture cache
  5) Perform ALL actions (Smart Fix + Optimize + Clean cache)
  6) Exit

Enter choice [1-6] (default: 5): 
```

---

## 🛠️ CLI Usage & Flags

| Action | Command |
|---|---|
| **Smart Fix (Recommended)** | `agy-beam --fix-mods --mode smart` |
| **Legacy Fix** | `agy-beam --fix-mods --mode legacy` |
| **Custom Mods Folder** | `agy-beam --mods-dir "D:\BeamNG\mods" --fix-mods` |
| **Optimize Graphics** | `agy-beam --optimize-graphics` |
| **Clean Shader Cache** | `agy-beam --clean-cache` |
| **All-in-One** | `agy-beam --all` |
| **Dry Run (Simulation)** | `agy-beam --all --dry-run` |

---

## 🧪 Testing

To run the full hermetic test suite:

```bash
python -m pytest -v
```

All 197 tests run hermetically against synthetic in-memory fixtures without modifying local game files.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
