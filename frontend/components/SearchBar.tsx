'use client';

import { useState } from 'react';

interface SearchBarProps {
  onSearch: (query: string) => Promise<void>;
}

export default function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    await onSearch(query.trim());
  };

  return (
    <form className="mb-6 flex flex-wrap items-center gap-2" onSubmit={submit}>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search title, author, genre, or summary"
        className="min-w-[260px] flex-1 rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
      />
      <button type="submit" className="rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white">
        Search
      </button>
      <button
        type="button"
        className="rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700"
        onClick={async () => {
          setQuery('');
          await onSearch('');
        }}
      >
        Clear
      </button>
    </form>
  );
}
