import { useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router";

// Add an entry here alongside each new top-level route.
const NAV_ENTRIES: { to: string; label: string; icon: ReactNode }[] = [
  { to: "/tenders", label: "Tenders", icon: <TendersIcon /> },
];

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={collapsed ? "layout layout--collapsed" : "layout"}>
      <aside className="sidebar">
        <div className="sidebar__header">
          <span className="sidebar__brand">
            <span className="sidebar__logo">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
                <path d="M5 6h14M12 6v13" />
              </svg>
            </span>
            <span className="sidebar__brand-name">TenderPy</span>
          </span>
          <button
            type="button"
            className="sidebar__toggle"
            onClick={() => setCollapsed((value) => !value)}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M9 4v16" />
              <path d={collapsed ? "M13 10l2 2-2 2" : "M16 10l-2 2 2 2"} />
            </svg>
          </button>
        </div>
        <nav className="sidebar__nav" aria-label="Main">
          {NAV_ENTRIES.map((entry) => (
            <NavLink
              key={entry.to}
              to={entry.to}
              className="sidebar__link"
              title={collapsed ? entry.label : undefined}
            >
              {entry.icon}
              <span className="sidebar__label">{entry.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <div className="main__content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function TendersIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 4h16v16H4z" />
      <path d="M4 9h16M9 9v11" />
    </svg>
  );
}
