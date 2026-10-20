import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { ENTRY_PATHS } from '../paths';
import { Icon } from './Icon';

const NAV = [
  ...ENTRY_PATHS.map((p) => ({ to: p.route, label: p.navLabel })),
  { to: '/prices', label: 'Prices' },
  { to: '/sources', label: 'Sources' },
];
const FOOTER_NAV = [...NAV, { to: '/about', label: 'About & limits' }];

export function Logo() {
  return (
    <Link to="/" className="logo" aria-label="PatientShield home">
      <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true" focusable="false">
        <path d="M16 2.5 4.5 6.8v8.4c0 7.2 4.9 12.6 11.5 14.3 6.6-1.7 11.5-7.1 11.5-14.3V6.8z" className="logo-shield" />
        <path d="M10.5 16.2l3.6 3.6 7.4-7.6" className="logo-check" />
      </svg>
      <span>PatientShield</span>
    </Link>
  );
}

export function Layout() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const firstRender = useRef(true);

  // After client-side navigation, move focus to the main region so screen-reader users hear the new page.
  // Skipped on first load so the skip link stays the first tab stop.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    document.getElementById('main')?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="prototype-banner" aria-label="Prototype notice">
        <Icon name="alert" size={16} />
        <span>
          Demo: use the <strong>synthetic samples</strong>, not real health information.
        </span>
      </aside>
      <header className="site-header">
        <div className="container header-inner">
          <Logo />
          <button
            type="button"
            className="menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="primary-nav"
            onClick={() => setMenuOpen((o) => !o)}
          >
            <Icon name={menuOpen ? 'close' : 'menu'} />
            <span className="visually-hidden">{menuOpen ? 'Close menu' : 'Open menu'}</span>
          </button>
          <nav id="primary-nav" aria-label="Primary" className={menuOpen ? 'nav open' : 'nav'}>
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <div>
            <Logo />
            <p className="footer-note">
              Educational tool for New Jersey health bills and denials. Not legal advice. Not approved for real health information.
            </p>
          </div>
          <nav aria-label="Footer" className="footer-links">
            {FOOTER_NAV.map((n) => (
              <Link key={n.to} to={n.to}>
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </>
  );
}
