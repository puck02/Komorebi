const navItems = ["Create", "History", "Assets"];

export default function App() {
  return (
    <main className="app-shell">
      <nav className="top-nav" aria-label="Primary navigation">
        <strong>Komorebi</strong>
        <div>
          {navItems.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </nav>
      <section className="hero-panel">
        <p className="eyebrow">AI Journal Scrapbook</p>
        <h1>把照片和几句话整理成温柔拼贴手帐。</h1>
      </section>
    </main>
  );
}
