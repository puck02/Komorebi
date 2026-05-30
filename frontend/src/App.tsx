import { Images, Library, NotebookPen } from "lucide-react";
import { NavLink, Route, Routes } from "react-router-dom";

import AssetLibraryPage from "./pages/AssetLibraryPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

const navItems = [
  { icon: NotebookPen, label: "创建", to: "/" },
  { icon: Images, label: "历史", to: "/history" },
  { icon: Library, label: "素材", to: "/assets" }
];

export default function App() {
  return (
    <main className="min-h-screen bg-[#f6efe7] text-[#2f2924]">
      <nav className="top-nav" aria-label="Primary navigation">
        <NavLink className="brand-link" to="/">
          Komorebi
        </NavLink>
        <div className="nav-actions">
          {navItems.map(({ icon: Icon, label, to }) => (
            <NavLink key={to} className={({ isActive }) => `nav-link ${isActive ? "is-active" : ""}`} to={to}>
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/history" element={<PlaceholderPage title="历史手帐" description="历史列表会在手帐保存接口完成后接入。" />} />
        <Route path="/assets" element={<AssetLibraryPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </main>
  );
}

function HomePage() {
  return (
    <section className="hero-panel">
      <p className="eyebrow">AI Journal Scrapbook</p>
      <h1>把照片和几句话整理成温柔拼贴手帐。</h1>
      <p className="hero-copy">生活照片、零碎心情和一点纸感装饰，会被整理成一页可以保存的日记手帐。</p>
    </section>
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
