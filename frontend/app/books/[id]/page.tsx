'use client';

import { useEffect, useState } from 'react';

import { Book } from '@/lib/types';

export default function BookDetailPage({ params }: { params: { id: string } }) {
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`/api/library/books/${params.id}`, { cache: 'no-store' });
        if (res.status === 404) {
          setBook(null);
          return;
        }
        if (!res.ok) {
          throw new Error('Unable to fetch book');
        }
        const data = (await res.json()) as Book;
        setBook(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Request failed');
      } finally {
        setLoading(false);
      }
    };

    void run();
  }, [params.id]);

  if (loading) {
    return <p>Loading book...</p>;
  }

  if (error) {
    return <p className="text-red-700">{error}</p>;
  }

  if (!book) {
    return <p>Book not found.</p>;
  }

  return (
    <section className="rounded-xl border border-zinc-300 bg-white p-6 shadow-sm">
      <h1 className="mb-2 text-3xl font-black text-zinc-900">{book.title}</h1>
      <p className="mb-1 text-zinc-700">Author: {book.author}</p>
      <p className="mb-1 text-zinc-700">Status: {book.status}</p>
      <p className="mb-1 text-zinc-600">Genre: {book.genre || 'N/A'}</p>
      {book.summary && <p className="mt-3 text-sm leading-6 text-zinc-600">{book.summary}</p>}
    </section>
  );
}
