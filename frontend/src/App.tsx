import { useState } from "react";
import { Images, Library, NotebookPen, UserRound } from "lucide-react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

import { clearAccessToken, getAccessToken } from "./api/client";
import AccountPage from "./pages/AccountPage";
import AssetLibraryPage from "./pages/AssetLibraryPage";
import CreateJournalPage from "./pages/CreateJournalPage";
import GenerationJobPage from "./pages/GenerationJobPage";
import InternalJournalRenderPage from "./pages/InternalJournalRenderPage";
import JournalDetailPage from "./pages/JournalDetailPage";
import JournalHistoryPage from "./pages/JournalHistoryPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

const navItems = [
  { icon: NotebookPen, label: "创建", to: "/" },
  { icon: Images, label: "历史", to: "/history" },
  { icon: Library, label: "素材", to: "/assets" },
  { icon: UserRound, label: "账号", to: "/account" }
];

export default function App() {
  if (window.location.pathname === "/internal/render") {
    return <InternalJournalRenderPage />;
  }

  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getAccessToken()));
  const handleAuthenticated = () => setIsAuthenticated(true);
  const handleLogout = () => {
    clearAccessToken();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-[#fffaf1] text-[#172c66]">
        <Routes>
          <Route path="/register" element={<RegisterPage onAuthenticated={handleAuthenticated} />} />
          <Route path="*" element={<LoginPage onAuthenticated={handleAuthenticated} />} />
        </Routes>
      </main>
    );
  }

  return (
    <main className="app-shell min-h-screen bg-[#fffaf1] text-[#172c66]">
      <nav className="top-nav" aria-label="Primary navigation">
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
        <Route path="/history" element={<JournalHistoryPage />} />
        <Route path="/journals/:journalId" element={<JournalDetailPage />} />
        <Route path="/generation/:jobId" element={<GenerationJobPage />} />
        <Route path="/assets" element={<AssetLibraryPage />} />
        <Route path="/account" element={<AccountPage onLogout={handleLogout} />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/register" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  );
}
