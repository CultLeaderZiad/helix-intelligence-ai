import React, { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import './PillNav.css';
import { useLanguage } from '@/context/LanguageContext';

export const PillNav = ({
  logo,
  logoAlt = 'Logo',
  items = [],
  activeHref = '',
  className = '',
  baseColor = '#0c0d0e',
  pillColor = '#181a1b',
  hoverCircleColor = '#ccff00',
  hoveredPillTextColor = '#000000',
  pillTextColor = '#ffffff',
  onMobileMenuClick = null,
  initialLoadAnimation = true
}) => {
  const { t } = useLanguage();
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
  /** @type {import('react').CSSProperties & Record<`--${string}`, string>} */
  const cssVars = {
    '--base': baseColor,
    '--pill-bg': pillColor,
    '--hover-circle': hoverCircleColor,
    '--hover-text': hoveredPillTextColor,
    '--pill-text': pillTextColor
  };

  const renderLink = (item, mobile = false) => {
    const routerLink = item.href && !isExternalLink(item.href);
    const content = mobile ? item.label : <>
      <span className="hover-circle" aria-hidden="true" />
      <span className="label-stack">
        <span className="pill-label">{item.label}</span>
        <span className="pill-label-hover" aria-hidden="true">{item.label}</span>
      </span>
    </>;
    const className = mobile
      ? `mobile-menu-link${activeHref === item.href ? ' is-active' : ''}${item.isPrimary ? ' is-primary' : ''}`
      : `pill${activeHref === item.href ? ' is-active' : ''}${item.isPrimary ? ' pill-primary' : ''}`;
    const onClick = mobile ? () => setIsMobileMenuOpen(false) : undefined;
    return routerLink ? (
      <Link to={item.href} className={className} aria-label={item.ariaLabel || item.label}
        aria-current={activeHref === item.href ? 'page' : undefined} onClick={onClick}>{content}</Link>
    ) : (
      <a href={item.href} className={className} aria-label={item.ariaLabel || item.label}
        aria-current={activeHref === item.href ? 'page' : undefined} onClick={onClick}>{content}</a>
    );
  };

  return (
    <div className={`pill-nav-container pill-nav-native${initialLoadAnimation ? ' pill-nav-enter' : ''}`}>
      <nav className={`pill-nav ${className}`} aria-label={t("primaryNavigation")} style={cssVars}>
        <Link className="pill-logo" to="/" aria-label={t("homeLink")}>
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
