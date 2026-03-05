'use client';

import { useEffect, useRef, useState } from 'react';
import { useUser } from '@auth0/nextjs-auth0/client';

export default function AccountMenu() {
  const { user, isLoading } = useUser();
  const [open, setOpen] = useState(false);
  const [pictureBroken, setPictureBroken] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!wrapperRef.current) {
        return;
      }
      if (!wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    window.addEventListener('mousedown', onClickOutside);
    window.addEventListener('keydown', onEscape);
    return () => {
      window.removeEventListener('mousedown', onClickOutside);
      window.removeEventListener('keydown', onEscape);
    };
  }, []);

  if (isLoading) {
    return <div className="h-10 w-10 rounded-full border border-zinc-300 bg-white" />;
  }

  if (!user) {
    return (
      <a
        href="/api/auth/login"
        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-zinc-300 bg-white text-zinc-700"
        aria-label="Login"
      >
        <span className="text-sm font-bold">in</span>
      </a>
    );
  }

  const initials = user.name
    ? user.name
        .split(' ')
        .map((chunk) => chunk[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : user.email
      ? user.email[0]?.toUpperCase() || 'U'
      : 'U';

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        className="inline-flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-zinc-300 bg-white"
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Open account menu"
      >
        {user.picture && !pictureBroken ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.picture}
            alt="Account"
            className="h-full w-full object-cover"
            onError={() => setPictureBroken(true)}
          />
        ) : (
          <span className="text-xs font-bold text-zinc-700">{initials}</span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-50 w-64 rounded-xl border border-zinc-300 bg-white p-3 shadow-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Signed in</p>
          <p className="mt-1 truncate text-sm font-medium text-zinc-800">{user.email || user.sub || 'Unknown account'}</p>
          <a
            href="/api/auth/logout"
            className="mt-3 inline-flex w-full items-center justify-center rounded-lg bg-zinc-900 px-3 py-2 text-sm font-semibold text-white"
          >
            Logout
          </a>
        </div>
      )}
    </div>
  );
}
