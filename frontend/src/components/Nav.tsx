"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FaBars,
  FaBus,
  FaComments,
  FaExclamationCircle,
  FaHome,
  FaShieldAlt,
  FaStar,
  FaTicketAlt,
  FaTimes,
} from "react-icons/fa";
import clsx from "clsx";

const links = [
  {
    href: "/",
    label: "Home",
    icon: FaHome,
  },
  {
    href: "/search",
    label: "Search",
    icon: FaBus,
  },
  {
    href: "/tickets",
    label: "My Tickets",
    icon: FaTicketAlt,
  },
  {
    href: "/assistant",
    label: "Assistant",
    icon: FaComments,
  },
  {
    href: "/complaints",
    label: "Complaints",
    icon: FaExclamationCircle,
  },
  {
    href: "/feedback",
    label: "Feedback",
    icon: FaStar,
  },
  {
    href: "/admin",
    label: "Admin",
    icon: FaShieldAlt,
  },
];

export function Nav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  function isActive(href: string) {
    if (href === "/") {
      return pathname === "/";
    }

    return (
      pathname === href ||
      pathname.startsWith(`${href}/`)
    );
  }

  function closeMobileMenu() {
    setMobileOpen(false);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link
          href="/"
          onClick={closeMobileMenu}
          className="flex items-center gap-2 font-bold text-brand-700"
        >
          <FaBus
            className="text-xl"
            aria-hidden
          />

          <span>BusMate</span>
        </Link>

        <nav
          className="hidden items-center gap-1 lg:flex"
          aria-label="Main navigation"
        >
          {links.map(
            ({
              href,
              label,
              icon: Icon,
            }) => (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition",
                  isActive(href)
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                )}
              >
                <Icon
                  className="text-base"
                  aria-hidden
                />

                <span>{label}</span>
              </Link>
            )
          )}
        </nav>

        <button
          type="button"
          onClick={() =>
            setMobileOpen(
              (current) => !current
            )
          }
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 lg:hidden"
          aria-label={
            mobileOpen
              ? "Close navigation menu"
              : "Open navigation menu"
          }
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? (
            <FaTimes />
          ) : (
            <FaBars />
          )}
        </button>
      </div>

      {mobileOpen && (
        <nav
          className="border-t border-slate-200 bg-white px-4 py-3 lg:hidden"
          aria-label="Mobile navigation"
        >
          <div className="mx-auto grid max-w-6xl gap-2 sm:grid-cols-2">
            {links.map(
              ({
                href,
                label,
                icon: Icon,
              }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={closeMobileMenu}
                  className={clsx(
                    "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition",
                    isActive(href)
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  <Icon
                    className="text-base"
                    aria-hidden
                  />

                  <span>{label}</span>
                </Link>
              )
            )}
          </div>
        </nav>
      )}
    </header>
  );
}