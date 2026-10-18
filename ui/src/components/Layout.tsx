import { useState } from "react";
import { NavLink, Outlet } from "react-router";

// Add an entry here alongside each new top-level route.
const NAV_ENTRIES = [{ to: "/tenders", label: "Tenders", short: "T" }];

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={collapsed ? "layout layout--collapsed" : "layout"}>
      <aside className="sidebar">
        <button
          type="button"
          className="sidebar__toggle"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? "»" : "«"}
        </button>
        <nav className="sidebar__nav">
          {NAV_ENTRIES.map((entry) => (
            <NavLink
              key={entry.to}
              to={entry.to}
              className="sidebar__link"
              title={entry.label}
            >
              {collapsed ? entry.short : entry.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
