'use client';

import { Book } from '@/lib/types';

interface BookModalProps {
  book: Book | null;
  open: boolean;
  isAuthenticated: boolean;
  currentUserSub?: string | null;
  isOwner: boolean;
  onClose: () => void;
  onBorrow: (book: Book) => void;
  onReturn: (bookId: number) => Promise<void>;
  onDelete: (bookId: number) => Promise<void>;
  onEnrich: (bookId: number) => Promise<void>;
  enrichingBookId?: number | null;
}

export default function BookModal({
  book,
  open,
  isAuthenticated,
  currentUserSub,
  isOwner,
  onClose,
  onBorrow,
  onReturn,
  onDelete,
  onEnrich,
  enrichingBookId
}: BookModalProps) {
  if (!open || !book) {
    return null;
  }

  const borrowed = book.status === 'borrowed';
  const borrowedByCurrentUser = Boolean(
    borrowed && isAuthenticated && currentUserSub && book.borrowed_by_auth0_id === currentUserSub
  );
  const borrowedByOtherUser = Boolean(borrowed && !borrowedByCurrentUser && book.borrowed_by_auth0_id);
  const borrowerLabel = book.borrowed_by_email || book.borrowed_by_auth0_id || (book.borrowed_by ? `User #${book.borrowed_by}` : 'N/A');

  const enriching = enrichingBookId === book.id;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" onClick={onClose}>
      <section
        className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl border border-zinc-300 bg-white p-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">Book Details</p>
            <h3 className="text-2xl font-bold text-zinc-900">{book.title}</h3>
            <p className="mt-1 text-sm text-zinc-600">by {book.author}</p>
          </div>
          <button
            className="rounded-lg border border-zinc-300 px-3 py-1 text-sm font-medium text-zinc-700"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>

        <div className="mb-4 overflow-hidden rounded-xl border border-zinc-200 bg-zinc-100">
          {book.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={book.image_url} alt={`${book.title} cover`} className="h-56 w-full object-cover" />
          ) : (
            <div className="flex h-56 items-center justify-center text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">
              No Image
            </div>
          )}
        </div>

        <div className="grid gap-3 rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-700 sm:grid-cols-2">
          <p>Status: <span className="font-semibold text-zinc-900">{book.status}</span></p>
          <p>Genre: <span className="font-semibold text-zinc-900">{book.genre || 'N/A'}</span></p>
          <p>Year: <span className="font-semibold text-zinc-900">{book.publication_year || 'N/A'}</span></p>
          <p>ISBN: <span className="font-semibold text-zinc-900">{book.isbn || 'N/A'}</span></p>
          <p>
            Borrowed By:{' '}
            <span className="font-semibold text-zinc-900">
              {borrowerLabel}
            </span>
          </p>
          <p>Due Date: <span className="font-semibold text-zinc-900">{book.due_date || 'N/A'}</span></p>
        </div>

        <div className="mt-4 rounded-xl border border-zinc-200 bg-white p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">Summary</p>
          <p className="text-sm leading-6 text-zinc-700">{book.summary || 'No summary added for this book yet.'}</p>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          {isOwner ? (
            <div className="flex w-full flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-medium text-zinc-600">
                {borrowed ? `Borrowed by: ${borrowerLabel}` : 'Available'}
              </p>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-xl border border-zinc-400 bg-white px-4 py-2 text-sm font-semibold text-zinc-900 disabled:opacity-50"
                  onClick={async () => {
                    await onEnrich(book.id);
                  }}
                  type="button"
                  disabled={enriching}
                >
                  {enriching ? 'Enriching...' : 'Enrich Metadata'}
                </button>
                <button
                  className="rounded-xl border border-zinc-400 bg-white px-4 py-2 text-sm font-semibold text-zinc-900"
                  onClick={async () => {
                    await onDelete(book.id);
                    onClose();
                  }}
                  type="button"
                >
                  Remove Book
                </button>
              </div>
            </div>
          ) : !borrowed ? (
            <button
              className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-semibold text-white"
              onClick={() => {
                onBorrow(book);
              }}
              type="button"
            >
              {isAuthenticated ? 'Borrow' : 'Login to Borrow'}
            </button>
          ) : (
            <button
              className={`rounded-xl border px-4 py-2 text-sm font-semibold ${
                borrowedByOtherUser
                  ? 'cursor-not-allowed border-zinc-300 bg-zinc-100 text-zinc-400'
                  : 'border-zinc-400 bg-white text-zinc-900'
              }`}
              onClick={async () => {
                if (borrowedByOtherUser) {
                  return;
                }
                await onReturn(book.id);
                onClose();
              }}
              disabled={borrowedByOtherUser}
              type="button"
            >
              {borrowedByOtherUser ? 'Borrowed by Another User' : isAuthenticated ? 'Return' : 'Login to Return'}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
