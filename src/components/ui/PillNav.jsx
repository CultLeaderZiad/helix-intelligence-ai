import React, { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import './PillNav.css';

export const PillNav = ({
  logo,
  logoAlt = 'Logo',
  items = [],
  activeHref,
  className = '',
  baseColor = '#0c0d0e',
  pillColor = '#181a1b',
  hoverCircleColor = '#ccff00',
  hoveredPillTextColor = '#000000',
  pillTextColor = '#ffffff',
  onMobileMenuClick,
  initialLoadAnimation = true
}) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuId = useId();
  const menuButtonRef = useRef(null);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [activeHref]);

  useEffect(() => {
    if (!isMobileMenuOpen) return;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsMobileMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isMobileMenuOpen]);

  const isExternalLink = (href) => /^(?:https?:|\/\/|mailto:|tel:|#)/.test(href || '');
  const cssVars = {
    '--base': baseColor,
    '--pill-bg': pillColor,
    '--hover-circle': hoverCircleColor,
    '--hover-text': hoveredPillTextColor,
    '--pill-text': pillTextColor
  };

  const renderLink = (item, mobile = false) => {
    const routerLink = item.href && !isExternalLink(item.href);
    const Component = routerLink ? Link : 'a';
    return (
      <Component
        {...(routerLink ? { to: item.href } : { href: item.href })}
        className={mobile
          ? `mobile-menu-link${activeHref === item.href ? ' is-active' : ''}${item.isPrimary ? ' is-primary' : ''}`
          : `pill${activeHref === item.href ? ' is-active' : ''}${item.isPrimary ? ' pill-primary' : ''}`}
        aria-label={item.ariaLabel || item.label}
        aria-current={activeHref === item.href ? 'page' : undefined}
        onClick={mobile ? () => setIsMobileMenuOpen(false) : undefined}
      >
        {mobile ? item.label : <>
          <span className="hover-circle" aria-hidden="true" />
          <span className="label-stack">
            <span className="pill-label">{item.label}</span>
            <span className="pill-label-hover" aria-hidden="true">{item.label}</span>
          </span>
        </>}
      </Component>
    );
  };

  return (
    <div className={`pill-nav-container pill-nav-native${initialLoadAnimation ? ' pill-nav-enter' : ''}`}>
      <nav className={`pill-nav ${className}`} aria-label="Primary" style={cssVars}>
        <Link className="pill-logo" to="/" aria-label="Helix Home">
          <img src={logo} alt={logoAlt} />
        </Link>
        <div className="pill-nav-items desktop-only">
          <ul className="pill-list">
            {items.map(item => <li key={item.href}>{renderLink(item)}</li>)}
          </ul>
        </div>
        <button
          type="button"
          className="mobile-menu-button mobile-only"
          onClick={() => {
            setIsMobileMenuOpen(open => !open);
            onMobileMenuClick?.();
          }}
          aria-label="Toggle menu"
          aria-expanded={isMobileMenuOpen}
          aria-controls={menuId}
          ref={menuButtonRef}
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>
      </nav>
      <div
        id={menuId}
        className="mobile-menu-popover mobile-only"
        hidden={!isMobileMenuOpen}
        style={cssVars}
      >
        <ul className="mobile-menu-list">
          {items.map(item => <li key={item.href}>{renderLink(item, true)}</li>)}
        </ul>
      </div>
    </div>
  );
};

export default PillNav;
