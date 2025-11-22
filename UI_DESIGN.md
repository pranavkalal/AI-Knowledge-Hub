# UI Design & Architecture: Next.js Knowledge Hub

## 1. Vision & Aesthetics
**Goal**: Create a "Premium SaaS" feel that inspires confidence and encourages exploration.
- **Theme**: "Clean Professional". **Light mode** by default, using crisp white backgrounds with subtle gray surfaces (`slate-50`). Accents: CRDC Green (Brand Color) for primary actions, deep navy for text.
- **Branding**: Prominent **CRDC Logo** in the header/sidebar.
- **Motion**: Subtle, fluid animations using `Framer Motion`. Elements should fade in, slide up, and expand naturally.
- **Typography**: `Inter` or `Geist Sans` for unmatched readability.

## 2. Tech Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (Radix Primitives)
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **State Management**: Zustand (for global UI state like sidebar toggle, current PDF view)
- **Data Fetching**: TanStack Query (React Query)

## 3. Core Layouts

### A. Landing Page ("The Portal")
- **Centerpiece**: A large, beautiful search bar with a glowing border effect.
- **Background**: Subtle animated gradient mesh or particle network.
- **Quick Starters**: Floating cards with suggested queries ("Cotton yield trends 2024", "Pest management strategies").

### B. The Workspace (Split View)
To support the "Deep Linking" requirement:
- **Left Panel (50%)**: Chat/Search Interface.
    - Streamed responses.
    - Citations appear as interactive badges `[S1]`. Hovering previews the text; clicking opens the source.
- **Right Panel (50%)**: Document Viewer (PDF.js).
    - Opens when a citation is clicked.
    - Auto-scrolls to the specific `bbox` (highlighted).
    - Can be collapsed to focus on chat.

## 4. Component Architecture (Atomic)

### Atoms (shadcn/ui base)
- `Button` (with custom glowing variants)
- `Input` / `Textarea` (auto-resizing)
- `Badge` (for citations)
- `Card` (for source previews)

### Molecules
- `CitationBadge`: Interactive pill that triggers the PDF viewer.
- `SourceCard`: Displays title, year, and a snippet of the source.
- `ChatMessage`: Renders Markdown + Citations. Handles streaming states.

### Organisms
- `ChatInterface`: Manages the message list and input area.
- `DocumentViewer`: Wraps PDF.js, handles zoom/navigation/highlighting.
- `Sidebar`: Navigation history and saved threads.

## 5. User Experience (UX) Enhancements
- **Skeleton Loading**: shimmering placeholders while AI thinks.
- **Optimistic UI**: Instant feedback when typing or clicking.
- **Keyboard Shortcuts**: `Cmd+K` to search, `Cmd+/` to focus chat.

## 6. Directory Structure
```
frontend/
├── app/
│   ├── layout.tsx       # Root layout (fonts, providers)
│   ├── page.tsx         # Landing page
│   └── chat/
│       └── [id]/        # Specific chat thread
├── components/
│   ├── ui/              # shadcn primitives
│   ├── chat/            # Chat-specific components
│   └── pdf/             # PDF viewer components
├── lib/
│   ├── api.ts           # FastAPI client
│   └── utils.ts         # Tailwind helpers
└── store/               # Zustand stores
```
