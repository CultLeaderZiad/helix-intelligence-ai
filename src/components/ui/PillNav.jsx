import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { gsap } from 'gsap';
import './PillNav.css';

/**
 * PillNav — the React Bits GSAP pill nav that ships on the live landing page
 * (helix-intelligence-ai-six.vercel.app), with the same timelines: a circle
 * that rises through each pill while the label rolls up, a logo spin, an
 * intro pop, and an animated hamburger + menu.
 *
 * Kept from the W3–W5 accessibility work: ordinary links in the Tab order (no
 * incomplete menubar role), aria-current, aria-expanded/aria-controls on the
 * menu button, Escape to close with focus return, keyboard focus playing the
 * same hover animation, translatable labels, and prefers-reduced-motion.
 *
 * @typedef {{ label: string, href: string, ariaLabel?: string, isPrimary?: boolean }} PillNavItem
 */

const isExternalLink = (/** @type {string} */ href) => /^(?:https?:|\/\/|mailto:|tel:)/.test(href || '') || (href || '').includes('#');

const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;

/**
 * @param {{
 *   logo: string, logoAlt?: string, logoHref?: string, items?: PillNavItem[], activeHref?: string,
 *   className?: string, ease?: string, baseColor?: string, pillColor?: string,
 *   hoverCircleColor?: string, hoveredPillTextColor?: string, pillTextColor?: string,
 *   onMobileMenuClick?: (() => void) | null, initialLoadAnimation?: boolean,
 *   ariaLabel?: string, homeLabel?: string, menuOpenLabel?: string, menuCloseLabel?: string
 * }} props
 */
export const PillNav = ({
  logo,
  logoAlt = 'Logo',
  logoHref = '/',
  items = [],
  activeHref = '',
  className = '',
  ease = 'power3.out',
  baseColor = '#0c0d0e',
  pillColor = '#181a1b',
  hoverCircleColor = '#ccff00',
  hoveredPillTextColor = '#000000',
  pillTextColor = '#ffffff',
  onMobileMenuClick = null,
  initialLoadAnimation = true,
  ariaLabel = 'Primary',
  homeLabel = 'Home',
  menuOpenLabel = 'Open menu',
  menuCloseLabel = 'Close menu'
}) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuId = useId();
  /** @type {import('react').MutableRefObject<(HTMLSpanElement | null)[]>} */
  const circleRefs = useRef([]);
  /** @type {import('react').MutableRefObject<(gsap.core.Timeline | null)[]>} */
  const tlRefs = useRef([]);
  /** @type {import('react').MutableRefObject<(gsap.core.Tween | null)[]>} */
  const activeTweenRefs = useRef([]);
  /** @type {import('react').RefObject<HTMLImageElement | null>} */
  const logoImgRef = useRef(null);
  /** @type {import('react').MutableRefObject<gsap.core.Tween | null>} */
  const logoTweenRef = useRef(null);
  /** @type {import('react').RefObject<HTMLButtonElement | null>} */
  const hamburgerRef = useRef(null);
  /** @type {import('react').RefObject<HTMLDivElement | null>} */
  const mobileMenuRef = useRef(null);
  /** @type {import('react').RefObject<HTMLDivElement | null>} */
  const navItemsRef = useRef(null);
  /** @type {import('react').RefObject<HTMLAnchorElement | null>} */
  const logoRef = useRef(null);
  const introPlayed = useRef(false);

  // Hover timelines: one per pill, sized from the pill's measured box so the
  // circle's arc spans the pill exactly (React Bits geometry).
  useLayoutEffect(() => {
    const layout = () => {
      circleRefs.current.forEach((circle, index) => {
        if (!circle?.parentElement) return;
        const pill = circle.parentElement;
        const { width: w, height: h } = pill.getBoundingClientRect();
        if (!w || !h) return;
        const R = ((w * w) / 4 + h * h) / (2 * h);
        const D = Math.ceil(2 * R) + 2;
        const delta = Math.ceil(R - Math.sqrt(Math.max(0, R * R - (w * w) / 4))) + 1;
        const originY = D - delta;

        circle.style.width = `${D}px`;
        circle.style.height = `${D}px`;
        circle.style.bottom = `-${delta}px`;
        gsap.set(circle, { xPercent: -50, scale: 0, transformOrigin: `50% ${originY}px` });

        const label = pill.querySelector('.pill-label');
        const white = pill.querySelector('.pill-label-hover');
        if (label) gsap.set(label, { y: 0 });
        if (white) gsap.set(white, { y: Math.ceil(h + 100), opacity: 0 });

        tlRefs.current[index]?.kill();
        const tl = gsap.timeline({ paused: true });
        tl.to(circle, { scale: 1.2, xPercent: -50, duration: 0.35, ease, overwrite: 'auto' }, 0);
        if (label) tl.to(label, { y: -(h + 8), duration: 0.35, ease, overwrite: 'auto' }, 0);
        if (white) tl.to(white, { y: 0, opacity: 1, duration: 0.35, ease, overwrite: 'auto' }, 0);
        tlRefs.current[index] = tl;
      });
    };

    layout();
    window.addEventListener('resize', layout);
    document.fonts?.ready?.then(layout).catch(() => {});

    if (initialLoadAnimation && !introPlayed.current && !reducedMotion()) {
      introPlayed.current = true;
      if (logoRef.current) gsap.fromTo(logoRef.current, { scale: 0 }, { scale: 1, duration: 0.6, ease });
      if (navItemsRef.current) gsap.fromTo(navItemsRef.current, { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration: 0.6, ease });
    }

    return () => window.removeEventListener('resize', layout);
  }, [items, ease, initialLoadAnimation]);

  // Scrub the paused timeline instead of replaying it, so moving quickly
  // between pills reverses smoothly from wherever the animation is.
  const handleEnter = (/** @type {number} */ i) => {
    const tl = tlRefs.current[i];
    if (!tl) return;
    activeTweenRefs.current[i]?.kill();
    activeTweenRefs.current[i] = tl.tweenTo(tl.duration(), { duration: reducedMotion() ? 0 : 0.3, ease, overwrite: 'auto' });
  };

  const handleLeave = (/** @type {number} */ i) => {
    const tl = tlRefs.current[i];
    if (!tl) return;
    activeTweenRefs.current[i]?.kill();
    activeTweenRefs.current[i] = tl.tweenTo(0, { duration: reducedMotion() ? 0 : 0.2, ease, overwrite: 'auto' });
  };

  const handleLogoEnter = () => {
    const img = logoImgRef.current;
    if (!img || reducedMotion()) return;
    logoTweenRef.current?.kill();
    gsap.set(img, { rotate: 0 });
    logoTweenRef.current = gsap.to(img, { rotate: 360, duration: 0.4, ease, overwrite: 'auto' });
  };

  // Hamburger morph + menu reveal follow the open state.
  useLayoutEffect(() => {
    const lines = hamburgerRef.current?.querySelectorAll('.hamburger-line');
    const duration = reducedMotion() ? 0 : 0.3;
    if (lines && lines.length >= 2) {
      gsap.to(lines[0], { rotation: isMobileMenuOpen ? 45 : 0, y: isMobileMenuOpen ? 3.5 : 0, duration, ease });
      gsap.to(lines[1], { rotation: isMobileMenuOpen ? -45 : 0, y: isMobileMenuOpen ? -3.5 : 0, duration, ease });
    }
    const menu = mobileMenuRef.current;
    if (menu && isMobileMenuOpen) {
      gsap.set(menu, { visibility: 'visible' });
      gsap.fromTo(menu, { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration, ease, transformOrigin: 'top center' });
    }
  }, [isMobileMenuOpen, ease]);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [activeHref]);

  useEffect(() => {
    if (!isMobileMenuOpen) return undefined;
    const onKeyDown = (/** @type {KeyboardEvent} */ event) => {
      if (event.key !== 'Escape') return;
      setIsMobileMenuOpen(false);
      hamburgerRef.current?.focus();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isMobileMenuOpen]);

  /** @type {import('react').CSSProperties & Record<`--${string}`, string>} */
  const cssVars = {
    '--base': baseColor,
    '--pill-bg': pillColor,
    '--hover-circle': hoverCircleColor,
    '--hover-text': hoveredPillTextColor,
    '--pill-text': pillTextColor
  };

  /** @param {PillNavItem} item @param {number} i */
  const renderPill = (item, i) => {
    const props = {
      className: `pill${activeHref === item.href ? ' is-active' : ''}${item.isPrimary ? ' pill-primary' : ''}`,
      'aria-label': item.ariaLabel || item.label,
      'aria-current': activeHref === item.href ? /** @type {'page'} */ ('page') : undefined,
      onMouseEnter: () => handleEnter(i),
      onMouseLeave: () => handleLeave(i),
      onFocus: () => handleEnter(i),
      onBlur: () => handleLeave(i)
    };
    const content = (
      <>
        <span className="hover-circle" aria-hidden="true" ref={el => { circleRefs.current[i] = el; }} />
        <span className="label-stack">
          <span className="pill-label">{item.label}</span>
          <span className="pill-label-hover" aria-hidden="true">{item.label}</span>
        </span>
      </>
    );
    return isExternalLink(item.href)
      ? <a href={item.href} {...props}>{content}</a>
      : <Link to={item.href} {...props}>{content}</Link>;
  };

  /** @param {PillNavItem} item */
  const renderMobileLink = item => {
    const props = {
      className: `mobile-menu-link${activeHref === item.href ? ' is-active' : ''}${item.isPrimary ? ' is-primary' : ''}`,
      'aria-current': activeHref === item.href ? /** @type {'page'} */ ('page') : undefined,
      onClick: () => setIsMobileMenuOpen(false)
    };
    return isExternalLink(item.href)
      ? <a href={item.href} {...props}>{item.label}</a>
      : <Link to={item.href} {...props}>{item.label}</Link>;
  };

  return (
    <div className="pill-nav-container">
      <nav className={`pill-nav ${className}`} aria-label={ariaLabel} style={cssVars}>
        <Link className="pill-logo" to={logoHref} aria-label={homeLabel} onMouseEnter={handleLogoEnter} ref={logoRef}>
          <img src={logo} alt={logoAlt} ref={logoImgRef} />
        </Link>

        <div className="pill-nav-items desktop-only" ref={navItemsRef}>
          <ul className="pill-list">
            {items.map((item, i) => <li key={item.href}>{renderPill(item, i)}</li>)}
          </ul>
        </div>

        <button
          type="button"
          className="mobile-menu-button mobile-only"
          onClick={() => {
            setIsMobileMenuOpen(open => !open);
            onMobileMenuClick?.();
          }}
          aria-label={isMobileMenuOpen ? menuCloseLabel : menuOpenLabel}
          aria-expanded={isMobileMenuOpen}
          aria-controls={menuId}
          ref={hamburgerRef}
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>
      </nav>

      <div id={menuId} className="mobile-menu-popover mobile-only" ref={mobileMenuRef} style={cssVars} hidden={!isMobileMenuOpen}>
        <ul className="mobile-menu-list">
          {items.map(item => <li key={item.href}>{renderMobileLink(item)}</li>)}
        </ul>
      </div>
    </div>
  );
};

export default PillNav;
