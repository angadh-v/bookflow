import type { Metadata } from 'next';
import { UserProvider } from '@auth0/nextjs-auth0/client';

import AccountMenu from '@/components/AccountMenu';

import './globals.css';

export const metadata: Metadata = {
  title: 'Library Management System',
  description: 'Technical assessment implementation with AI-assisted search'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <UserProvider>
          <div className="mx-auto max-w-7xl px-4 py-6">
            <header className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-300 bg-white/85 p-4 shadow-[0_12px_26px_-22px_rgba(0,0,0,0.9)] backdrop-blur">
              <a href="/" className="text-xl font-black tracking-tight text-zinc-900">
                BookFlow
              </a>
              <nav className="flex items-center gap-3 text-sm font-medium">
                <AccountMenu />
              </nav>
            </header>
            {children}
            <footer className="mt-10 border-t border-zinc-300 pt-4 text-center text-sm text-zinc-600">
              Made by Angadh Verma. 
              Source code available on <a href="https://github.com/angadh/library-management" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">GitHub</a>.
            </footer>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}
