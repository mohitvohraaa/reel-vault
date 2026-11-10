import {
  FolderOpen,
  LayoutDashboard,
  Library,
  Moon,
  Search,
  Sun,
  Upload,
  Brain,
} from "lucide-react";
import { NavLink, Route, Routes } from "react-router-dom";
import { useTheme } from "./hooks/useTheme";
import { cn } from "./lib/utils";
import Dashboard from "./pages/Dashboard";
import ImportPage from "./pages/Import";
import LibraryPage from "./pages/LibraryPage";
import ReelDetailPage from "./pages/ReelDetail";
import SearchPage from "./pages/SearchPage";
import Collections from "./pages/Collections";
import KnowledgeBases from "./pages/KnowledgeBases";
import KnowledgeBaseDetail from "./pages/KnowledgeBaseDetail";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/library", label: "Library", icon: Library },
  { to: "/search", label: "Search", icon: Search },
  { to: "/collections", label: "Collections", icon: FolderOpen },
  { to: "/knowledge-bases", label: "Knowledge Bases", icon: Brain },
  { to: "/import", label: "Import", icon: Upload },
];

export default function App() {
  const { theme, toggle } = useTheme();
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-surface px-3 py-5 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white">
            <Library className="h-4 w-4" />
          </div>
          <span className="text-lg font-semibold tracking-tight">ReelVault</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-accent/10 text-accent" : "text-muted hover:bg-bg hover:text-fg"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button onClick={toggle} className="btn-ghost justify-start">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </aside>

      <main className="flex-1 overflow-x-hidden">
        {/* Mobile top bar */}
        <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 md:hidden">
          <span className="text-lg font-semibold">ReelVault</span>
          <button onClick={toggle} className="btn-ghost p-2">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
        <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/reels/:id" element={<ReelDetailPage />} />
            <Route path="/collections" element={<Collections />} />
            <Route path="/knowledge-bases" element={<KnowledgeBases />} />
            <Route path="/knowledge-bases/:id" element={<KnowledgeBaseDetail />} />
            <Route path="/import" element={<ImportPage />} />
          </Routes>
        </div>
        {/* Mobile bottom nav */}
        <nav className="sticky bottom-0 flex items-center justify-around border-t border-border bg-surface py-2 md:hidden">
          {NAV.slice(0, 5).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => cn("flex flex-col items-center gap-0.5 px-2 text-[10px]", isActive ? "text-accent" : "text-muted")}
            >
              <item.icon className="h-5 w-5" />
            </NavLink>
          ))}
        </nav>
      </main>
    </div>
  );
}
