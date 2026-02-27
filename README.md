# REDSHELL — Automated Red Team Intelligence Platform

> Paste a GitHub URL. We clone it, build it, attack it, and hand you a penetration testing report — fully automated.

Built at **Inceptrix 2026**.

---

## Tech Stack

- **React 19** + **TypeScript 5.9**
- **Vite 7** (dev server + bundler)
- **Tailwind CSS v4** (via `@tailwindcss/vite`)
- **Spline** (3D interactive globe)
- **Google Fonts** — Bebas Neue, JetBrains Mono, Space Mono

---

## Prerequisites

- **Node.js** ≥ 18 (LTS recommended)
- **npm** ≥ 9 (ships with Node) — or **pnpm** / **yarn**

---

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/<your-org>/inceptrix2026.git
cd inceptrix2026

# 2. Navigate to the frontend
cd frontend

# 3. Install dependencies
npm install

# 4. Start the dev server
npm run dev
```

The app will be available at **http://localhost:5173**.

---

## Available Scripts

| Command            | Description                          |
| ------------------ | ------------------------------------ |
| `npm run dev`      | Start Vite dev server with HMR       |
| `npm run build`    | Type-check & production build        |
| `npm run preview`  | Preview the production build locally  |
| `npm run lint`     | Run ESLint across the project         |

---

## Project Structure

```
frontend/
├── index.html              # Entry HTML (fonts, meta)
├── vite.config.ts          # Vite + Tailwind + React config
├── tsconfig.json           # TypeScript project references
├── public/                 # Static assets
└── src/
    ├── main.tsx            # React root mount
    ├── App.tsx             # App shell (sections + overlay effects)
    ├── index.css           # Tailwind v4 @theme tokens + globals
    ├── App.css             # Keyframe animations + component styles
    ├── components/
    │   ├── HeroSection.tsx       # Hero with headline + Spline globe
    │   ├── ScanInputPanel.tsx    # Terminal-style URL input
    │   ├── PipelineSection.tsx   # 4-phase attack pipeline
    │   ├── FooterCTA.tsx         # Closing CTA + footer
    │   └── SplineGlobe.tsx       # Spline 3D loader with fallback
    ├── hooks/
    │   ├── useInView.ts          # Intersection Observer hook
    │   └── useCountUp.ts         # Animated counter hook
    └── data/
        └── mockData.ts           # Mock stats + terminal lines
```

---

## Building for Production

```bash
cd frontend
npm run build
```

Output goes to `frontend/dist/`. Serve it with any static host (Vercel, Netlify, Cloudflare Pages, etc.) or preview locally:

```bash
npm run preview
```

---

## License

MIT
