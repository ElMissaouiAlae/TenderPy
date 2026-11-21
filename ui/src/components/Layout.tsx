import { useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router";

// Add an entry here alongside each new top-level route. The top bar's title
// is the label of the entry the current URL falls under.
const NAV_ENTRIES: { to: string; label: string; icon: ReactNode }[] = [
  { to: "/tenders", label: "Tenders", icon: <TendersIcon /> },
];

function currentTitle(pathname: string): string {
  const entry = NAV_ENTRIES.find(
    ({ to }) => pathname === to || pathname.startsWith(`${to}/`),
  );
  return entry?.label ?? "TenderPy";
}

export function Layout() {
  const location = useLocation();
  // Only has an effect at phone width, where the sidebar is a drawer.
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);

  // Navigating closes the drawer.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.key]);

  // Hands focus back to the menu button, since the drawer it was in is
  // about to be hidden.
  function closeMenu() {
    setMenuOpen(false);
    menuButtonRef.current?.focus();
  }

  useEffect(() => {
    if (!menuOpen) return;
    // The drawer comes before the menu button in the page, so move focus
    // into it; otherwise Tab would walk on into the page content.
    navRef.current?.querySelector<HTMLElement>("a")?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") closeMenu();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  return (
    <div className={menuOpen ? "layout layout--menu-open" : "layout"}>
      <aside className="sidebar" id="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__logo">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
              <path d="M5 6h14M12 6v13" />
            </svg>
          </span>
          <span className="sidebar__brand-name">TenderPy</span>
        </div>
        <nav className="sidebar__nav" aria-label="Main" ref={navRef}>
          {NAV_ENTRIES.map((entry) => (
            <NavLink
              key={entry.to}
              to={entry.to}
              className="sidebar__link"
              onClick={menuOpen ? closeMenu : undefined}
            >
              {entry.icon}
              <span>{entry.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      {/* Phone width only: clicking beside the open drawer closes it. */}
      <div className="layout__backdrop" aria-hidden="true" onClick={closeMenu} />
      <div className="main">
        <header className="topbar">
          <button
            ref={menuButtonRef}
            type="button"
            className="topbar__menu"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Menu"
            aria-expanded={menuOpen}
            aria-controls="sidebar"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="topbar__title">{currentTitle(location.pathname)}</h1>
        </header>
        <main className="main__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function TendersIcon() {
  return (
    <svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <path d="M14 3v6h6M8 13h8M8 17h5" />
    </svg>
  );
}
