'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@auth0/nextjs-auth0/client';

import BookCard from '@/components/BookCard';
import BookModal from '@/components/BookModal';
import ChatInterface from '@/components/ChatInterface';
import SearchBar from '@/components/SearchBar';
import { checkinBook, checkoutBook, createBook, deleteBook, enrichBook, getBooks, searchBooks } from '@/lib/api';
import { Book } from '@/lib/types';

interface CreateFormState {
  title: string;
  author: string;
  isbn: string;
  publication_year: string;
  genre: string;
  image_url: string;
  summary: string;
}

interface ConfirmationOverlayState {
  title: string;
  message: string;
}

const initialForm: CreateFormState = {
  title: '',
  author: '',
  isbn: '',
  publication_year: '',
  genre: '',
  image_url: '',
  summary: ''
};

const PICKUP_LOCATION = 'McGill Library, 3459 McTavish St, Montreal, QC H3A 0C9';

function defaultPickupDateTime(): string {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(10, 0, 0, 0);

  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatPickupDateTime(value: string): string {
  if (!value) {
    return 'your selected pickup time';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export default function CataloguePage() {
  const { user, isLoading } = useUser();
  const ownerSub = (process.env.NEXT_PUBLIC_OWNER_AUTH0_SUB || '').trim();
  const isOwner = Boolean(user?.sub && ownerSub && user.sub === ownerSub);

  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authOverlayMessage, setAuthOverlayMessage] = useState<string | null>(null);
  const [authOverlayCanLogin, setAuthOverlayCanLogin] = useState(false);
  const [form, setForm] = useState<CreateFormState>(initialForm);
  const [showMoreFields, setShowMoreFields] = useState(false);
  const [activeBook, setActiveBook] = useState<Book | null>(null);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [columns, setColumns] = useState(3);
  const [currentPage, setCurrentPage] = useState(1);
  const [borrowRequestBook, setBorrowRequestBook] = useState<Book | null>(null);
  const [pickupTime, setPickupTime] = useState(defaultPickupDateTime());
  const [borrowSubmitting, setBorrowSubmitting] = useState(false);
  const [confirmationOverlay, setConfirmationOverlay] = useState<ConfirmationOverlayState | null>(null);
  const [enrichingBookId, setEnrichingBookId] = useState<number | null>(null);

  const pageSize = columns * 2;
  const totalPages = Math.max(1, Math.ceil(books.length / pageSize));
  const pageStart = (currentPage - 1) * pageSize;
  const paginatedBooks = books.slice(pageStart, pageStart + pageSize);

  const loadBooks = async (showLoader = false) => {
    try {
      if (showLoader) {
        setLoading(true);
      }
      setError(null);
      const data = await getBooks();
      setBooks(data);
      setCurrentPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load books');
    } finally {
      if (showLoader) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    void loadBooks(true);
  }, []);

  useEffect(() => {
    const updateColumns = () => {
      const width = window.innerWidth;
      if (width >= 1280) {
        setColumns(3);
      } else if (width >= 640) {
        setColumns(2);
      } else {
        setColumns(1);
      }
    };

    updateColumns();
    window.addEventListener('resize', updateColumns);
    return () => window.removeEventListener('resize', updateColumns);
  }, []);

  useEffect(() => {
    setCurrentPage((prev) => Math.min(prev, totalPages));
  }, [totalPages]);

  useEffect(() => {
    if (!confirmationOverlay) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setConfirmationOverlay(null);
    }, 2000);
    return () => window.clearTimeout(timeoutId);
  }, [confirmationOverlay]);

  const showAuthOverlay = (message: string, canLogin: boolean) => {
    setAuthOverlayCanLogin(canLogin);
    setAuthOverlayMessage(message);
  };

  const handleSearch = async (query: string) => {
    try {
      setError(null);
      if (!query) {
        await loadBooks();
        return;
      }
      const data = await searchBooks(query);
      setBooks(data);
      setCurrentPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    }
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!user) {
      showAuthOverlay('Log in to add books.', true);
      return;
    }
    if (!isOwner) {
      showAuthOverlay('Only the owner can add books.', false);
      return;
    }

    if (!form.title.trim() || !form.author.trim()) {
      setError('Title and author are required');
      return;
    }

    const publicationYear = form.publication_year.trim() ? Number(form.publication_year.trim()) : undefined;
    if (publicationYear && Number.isNaN(publicationYear)) {
      setError('Year must be a valid number');
      return;
    }

    try {
      setError(null);
      await createBook({
        title: form.title.trim(),
        author: form.author.trim(),
        isbn: form.isbn.trim() || undefined,
        publication_year: publicationYear,
        genre: form.genre.trim() || undefined,
        image_url: form.image_url.trim() || undefined,
        summary: form.summary.trim() || undefined
      });
      setForm(initialForm);
      setShowMoreFields(false);
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    }
  };

  const handleBorrow = (book: Book) => {
    if (!user) {
      showAuthOverlay('Log in to borrow books.', true);
      return;
    }
    setActiveBook(null);
    setBorrowRequestBook(book);
    setPickupTime(defaultPickupDateTime());
  };

  const handleBorrowConfirm = async () => {
    if (!borrowRequestBook || !user) {
      return;
    }
    if (!pickupTime) {
      setError('Pickup time is required.');
      return;
    }

    try {
      setBorrowSubmitting(true);
      setError(null);
      await checkoutBook(borrowRequestBook.id);
      await loadBooks();
      setBorrowRequestBook(null);
      setConfirmationOverlay({
        title: 'Borrow Request Submitted',
        message: `Confirmation sent to ${user.email || 'your email'}. Pickup at ${formatPickupDateTime(pickupTime)}.`
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Borrow request failed');
    } finally {
      setBorrowSubmitting(false);
    }
  };

  const handleReturn = async (bookId: number) => {
    if (!user) {
      showAuthOverlay('Log in to return books.', true);
      return;
    }

    try {
      setError(null);
      await checkinBook(bookId);
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Return failed');
    }
  };

  const handleDelete = async (bookId: number) => {
    if (!user) {
      showAuthOverlay('Log in as owner to remove books.', true);
      return;
    }
    if (!isOwner) {
      showAuthOverlay('Only the owner can remove books.', false);
      return;
    }
    if (!window.confirm('Remove this book?')) {
      return;
    }

    try {
      setError(null);
      await deleteBook(bookId);
      setBooks((prev) => prev.filter((book) => book.id !== bookId));
      if (activeBook?.id === bookId) {
        setActiveBook(null);
      }
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Remove failed');
    }
  };

  const handleEnrich = async (bookId: number) => {
    if (!user) {
      showAuthOverlay('Log in as owner to enrich metadata.', true);
      return;
    }
    if (!isOwner) {
      showAuthOverlay('Only the owner can enrich metadata.', false);
      return;
    }

    try {
      setError(null);
      setEnrichingBookId(bookId);
      const updated = await enrichBook(bookId);
      setBooks((prev) => prev.map((book) => (book.id === bookId ? updated : book)));
      setActiveBook((prev) => (prev?.id === bookId ? updated : prev));
      setConfirmationOverlay({
        title: 'Metadata Enriched',
        message: 'Missing fields were enriched using AI where available.'
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Metadata enrichment failed');
    } finally {
      setEnrichingBookId(null);
    }
  };

  if (isLoading) {
    return <p className="text-center text-sm text-zinc-600">Loading session...</p>;
  }

  return (
    <>
      <main className="mx-auto grid max-w-6xl gap-6 pb-24">
        <section className="rounded-2xl border border-zinc-300 bg-white p-8 text-center shadow-[0_14px_28px_-24px_rgba(0,0,0,0.85)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-zinc-500">Library</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-zinc-900 md:text-5xl">Library Management System</h1>
          <p className="mt-3 text-base text-zinc-600">
            {user ? 'Browse and borrow books with streamlined lending requests.' : 'Browse books as a guest. Sign in to borrow.'}
          </p>
        </section>

        <section className="rounded-2xl border border-zinc-300 bg-white p-6 text-center">
          <h2 className="mb-4 text-2xl font-bold text-zinc-900 md:text-3xl">Catalogue</h2>
          <SearchBar onSearch={handleSearch} />

          {error && (
            <p className="mx-auto mb-4 max-w-2xl rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          {loading ? (
            <p className="text-sm text-zinc-600">Loading books...</p>
          ) : (
            <>
              <div className="grid justify-items-center gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {paginatedBooks.map((book) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    onOpen={setActiveBook}
                    isAuthenticated={Boolean(user)}
                    currentUserSub={user?.sub ?? null}
                    isOwner={isOwner}
                    onBorrow={handleBorrow}
                    onReturn={handleReturn}
                    onDelete={handleDelete}
                  />
                ))}
                {books.length === 0 && <p className="text-sm text-zinc-600">No books found.</p>}
              </div>

              {books.length > pageSize && (
                <div className="mt-5 flex items-center justify-center gap-3">
                  <button
                    className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-semibold text-zinc-700 disabled:opacity-40"
                    onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    type="button"
                  >
                    Previous
                  </button>
                  <p className="text-sm font-semibold text-zinc-600">
                    Page {currentPage} of {totalPages}
                  </p>
                  <button
                    className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-semibold text-zinc-700 disabled:opacity-40"
                    onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    type="button"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </section>

        {isOwner ? (
          <section className="mx-auto w-full max-w-3xl rounded-2xl border border-zinc-300 bg-white p-5">
            <div className="mb-3 text-center">
              <h2 className="text-xl font-bold text-zinc-900 md:text-2xl">Add New Book</h2>
              <p className="mt-1 text-sm text-zinc-500">Only title and author are required.</p>
            </div>

            <form className="grid gap-3 md:grid-cols-2" onSubmit={handleCreate}>
              <input
                className="rounded-xl border border-zinc-300 px-3 py-2 text-sm"
                placeholder="Title *"
                value={form.title}
                onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
              />
              <input
                className="rounded-xl border border-zinc-300 px-3 py-2 text-sm"
                placeholder="Author *"
                value={form.author}
                onChange={(event) => setForm((prev) => ({ ...prev, author: event.target.value }))}
              />

              {showMoreFields && (
                <>
                  <input
                    className="rounded-xl border border-zinc-300 px-3 py-2 text-sm"
                    placeholder="ISBN"
                    value={form.isbn}
                    onChange={(event) => setForm((prev) => ({ ...prev, isbn: event.target.value }))}
                  />
                  <input
                    className="rounded-xl border border-zinc-300 px-3 py-2 text-sm"
                    placeholder="Publication Year"
                    value={form.publication_year}
                    onChange={(event) => setForm((prev) => ({ ...prev, publication_year: event.target.value }))}
                    inputMode="numeric"
                  />
                  <input
                    className="rounded-xl border border-zinc-300 px-3 py-2 text-sm md:col-span-2"
                    placeholder="Genre"
                    value={form.genre}
                    onChange={(event) => setForm((prev) => ({ ...prev, genre: event.target.value }))}
                  />
                  <input
                    className="rounded-xl border border-zinc-300 px-3 py-2 text-sm md:col-span-2"
                    placeholder="Image URL"
                    value={form.image_url}
                    onChange={(event) => setForm((prev) => ({ ...prev, image_url: event.target.value }))}
                  />
                  <textarea
                    className="min-h-24 rounded-xl border border-zinc-300 px-3 py-2 text-sm md:col-span-2"
                    placeholder="Summary"
                    value={form.summary}
                    onChange={(event) => setForm((prev) => ({ ...prev, summary: event.target.value }))}
                  />
                </>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 md:col-span-2">
                <button
                  className="rounded-lg border border-zinc-300 bg-zinc-100 px-3 py-2 text-sm font-semibold text-zinc-700"
                  type="button"
                  onClick={() => setShowMoreFields((prev) => !prev)}
                >
                  {showMoreFields ? 'Hide More Fields' : 'Show More Fields'}
                </button>
                <button className="rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white" type="submit">
                  Add Book
                </button>
              </div>
            </form>
          </section>
        ) : (
          <section className="mx-auto w-full max-w-3xl rounded-2xl border border-zinc-300 bg-white p-5 text-center">
            <h2 className="text-xl font-bold text-zinc-900">Editing Access</h2>
            <p className="mt-2 text-sm text-zinc-600">
              Add/remove is restricted to the owner role. Client accounts can browse and borrow books.
            </p>
          </section>
        )}
      </main>

      <BookModal
        book={activeBook}
        open={Boolean(activeBook)}
        isAuthenticated={Boolean(user)}
        currentUserSub={user?.sub ?? null}
        isOwner={isOwner}
        onClose={() => setActiveBook(null)}
        onBorrow={handleBorrow}
        onReturn={handleReturn}
        onDelete={handleDelete}
        onEnrich={handleEnrich}
        enrichingBookId={enrichingBookId}
      />

      {authOverlayMessage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4"
          onClick={() => {
            setAuthOverlayMessage(null);
            setAuthOverlayCanLogin(false);
          }}
        >
          <section
            className="w-full max-w-md rounded-2xl border border-zinc-300 bg-white p-5 text-center shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-zinc-900">{authOverlayCanLogin ? 'Login Required' : 'Action Restricted'}</h3>
            <p className="mt-2 text-sm text-zinc-600">{authOverlayMessage}</p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-semibold text-zinc-700"
                onClick={() => {
                  setAuthOverlayMessage(null);
                  setAuthOverlayCanLogin(false);
                }}
                type="button"
              >
                Close
              </button>
              {authOverlayCanLogin && (
                <a href="/api/auth/login" className="rounded-lg bg-zinc-900 px-3 py-2 text-sm font-semibold text-white">
                  Login
                </a>
              )}
            </div>
          </section>
        </div>
      )}

      {borrowRequestBook && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4" onClick={() => setBorrowRequestBook(null)}>
          <section
            className="w-full max-w-lg rounded-2xl border border-zinc-300 bg-white p-5 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-zinc-900">Borrow Request</h3>
            <p className="mt-2 text-sm text-zinc-600">
              Confirm pickup details for <span className="font-semibold text-zinc-900">{borrowRequestBook.title}</span>.
            </p>
            <div className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-700">
              <p className="font-semibold text-zinc-900">Pickup Location</p>
              <p className="mt-1">{PICKUP_LOCATION}</p>
            </div>
            <label className="mt-4 block text-sm font-semibold text-zinc-700" htmlFor="pickup-time">
              Pickup Time
            </label>
            <input
              id="pickup-time"
              type="datetime-local"
              className="mt-2 w-full rounded-xl border border-zinc-300 px-3 py-2 text-sm"
              value={pickupTime}
              onChange={(event) => setPickupTime(event.target.value)}
            />
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm font-semibold text-zinc-700"
                onClick={() => setBorrowRequestBook(null)}
                disabled={borrowSubmitting}
                type="button"
              >
                Cancel
              </button>
              <button
                className="rounded-lg bg-zinc-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                onClick={() => void handleBorrowConfirm()}
                disabled={borrowSubmitting}
                type="button"
              >
                {borrowSubmitting ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>
          </section>
        </div>
      )}

      {confirmationOverlay && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-4"
          onClick={() => setConfirmationOverlay(null)}
        >
          <section
            className="w-full max-w-lg rounded-2xl border border-zinc-300 bg-white p-5 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-zinc-900">{confirmationOverlay.title}</h3>
            <p className="mt-2 text-sm text-zinc-600">{confirmationOverlay.message}</p>
            <p className="mt-3 text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">Closing automatically...</p>
          </section>
        </div>
      )}

      <button
        className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm font-bold text-white shadow-[0_18px_30px_-12px_rgba(0,0,0,0.85)] ring-2 ring-white/70 transition hover:-translate-y-0.5 hover:bg-black"
        onClick={() => setAssistantOpen(true)}
        type="button"
      >
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white text-zinc-900">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path
              d="M8 9.5h8M8 13h5m-7 7 2.6-2h8.4A3 3 0 0 0 20 15V7a3 3 0 0 0-3-3H7A3 3 0 0 0 4 7v8a3 3 0 0 0 2 2.83V20Z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        Assistant
      </button>

      {assistantOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/35" onClick={() => setAssistantOpen(false)} />
          <aside className="fixed right-0 top-0 z-50 h-full w-full max-w-md border-l border-zinc-300 bg-zinc-100 p-4 pt-6 shadow-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xl font-bold text-zinc-900">Assistant</h2>
              <button
                className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm font-semibold text-zinc-700"
                onClick={() => setAssistantOpen(false)}
                type="button"
              >
                Close
              </button>
            </div>

            {user ? (
              <ChatInterface hideTitle className="h-[calc(100vh-5.5rem)] border-zinc-200" />
            ) : (
              <div className="rounded-2xl border border-zinc-300 bg-white p-4 text-sm text-zinc-700">
                <p>Log in to use the assistant.</p>
                <a
                  href="/api/auth/login"
                  className="mt-3 inline-flex rounded-lg bg-zinc-900 px-3 py-2 font-semibold text-white"
                >
                  Login
                </a>
              </div>
            )}
          </aside>
        </>
      )}
    </>
  );
}
