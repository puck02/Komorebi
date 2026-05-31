import { useState } from "react";
import { Images, Library, NotebookPen } from "lucide-react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

import { getAccessToken } from "./api/client";
import AssetLibraryPage from "./pages/AssetLibraryPage";
import CreateJournalPage from "./pages/CreateJournalPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

const navItems = [
  { icon: NotebookPen, label: "创建", to: "/" },
  { icon: Images, label: "历史", to: "/history" },
  { icon: Library, label: "素材", to: "/assets" }
];

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getAccessToken()));
  const handleAuthenticated = () => setIsAuthenticated(true);

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-[#f6efe7] text-[#2f2924]">
        <Routes>
          <Route path="/register" element={<RegisterPage onAuthenticated={handleAuthenticated} />} />
          <Route path="*" element={<LoginPage onAuthenticated={handleAuthenticated} />} />
        </Routes>
      </main>
    );
  }

  return (
    <main className="app-shell min-h-screen bg-[#f6efe7] text-[#2f2924]">
      <nav className="top-nav backdrop-blur-md bg-white/70" aria-label="Primary navigation">
        <NavLink className="brand-link" to="/">
          Komorebi
        </NavLink>
        <div className="nav-actions">
          {navItems.map(({ icon: Icon, label, to }) => (
            <NavLink
              key={to}
              aria-label={label}
              className={({ isActive }) => `nav-link ${isActive ? "is-active" : ""}`}
              to={to}
            >
              <Icon size={16} />
              <span className="nav-label">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<CreateJournalPage />} />
        <Route path="/history" element={<PlaceholderPage title="历史手帐" description="历史列表会在手帐保存接口完成后接入。" />} />
        <Route path="/journals/:journalId" element={<PlaceholderPage title="手帐详情" description="详情预览和轻量编辑会在下一步接入。" />} />
        <Route path="/assets" element={<AssetLibraryPage />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/register" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  );
}

type PlaceholderPageProps = {
  title: string;
  description: string;
};

function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className="mx-auto grid max-w-5xl gap-3 px-5 py-20">
      <p className="eyebrow">Coming next</p>
      <h1 className="text-4xl font-semibold">{title}</h1>
      <p className="max-w-xl text-[#65584d]">{description}</p>
    </section>
  );
}
