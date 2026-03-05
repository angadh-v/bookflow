'use client';

import { Book } from '@/lib/types';

interface BookCardProps {
  book: Book;
  onOpen: (book: Book) => void;
  isAuthenticated: boolean;
  currentUserSub?: string | null;
  isOwner: boolean;
  onBorrow: (book: Book) => void;
  onReturn: (bookId: number) => Promise<void>;
  onDelete: (bookId: number) => Promise<void>;
}

export default function BookCard({
  book,
  onOpen,
  isAuthenticated,
  currentUserSub,
  isOwner,
  onBorrow,
  onReturn,
  onDelete
}: BookCardProps) {
  const borrowed = book.status === 'borrowed';
  const borrowedByCurrentUser = Boolean(
    borrowed && isAuthenticated && currentUserSub && book.borrowed_by_auth0_id === currentUserSub
  );
  const borrowedByOtherUser = Boolean(borrowed && !borrowedByCurrentUser && book.borrowed_by_auth0_id);
  const borrowerLabel = book.borrowed_by_email || book.borrowed_by_auth0_id || (book.borrowed_by ? `User #${book.borrowed_by}` : null);

  return (
    <article
      className="group w-full max-w-sm cursor-pointer rounded-2xl border border-zinc-300 bg-white p-4 shadow-[0_10px_20px_-16px_rgba(0,0,0,0.65)] transition hover:border-zinc-500 hover:shadow-[0_18px_30px_-20px_rgba(0,0,0,0.75)]"
      onClick={() => onOpen(book)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen(book);
        }
      }}
    >
      <div className="mb-3 overflow-hidden rounded-xl border border-zinc-200 bg-zinc-100">
        {book.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={book.image_url}
            alt={`${book.title} cover`}
            className="h-44 w-full object-cover"
            onError={(event) => {
              event.currentTarget.style.display = 'none';
            }}
          />
        ) : (
          <div className="flex h-44 items-center justify-center text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">
            No Image
          </div>
        )}
      </div>

      <div className="mb-3 flex items-start justify-between gap-2">
        <h3 className="text-lg font-bold text-zinc-900 group-hover:text-black">{book.title}</h3>
        <span
          className={`rounded-full px-2 py-1 text-xs font-semibold ${
            borrowed ? 'bg-zinc-900 text-white' : 'bg-zinc-100 text-zinc-800'
          }`}
        >
          {book.status}
        </span>
      </div>
      <p className="text-sm text-zinc-700">Author: {book.author}</p>
      <p className="text-sm text-zinc-600">Genre: {book.genre || 'N/A'}</p>
      <p className="text-sm text-zinc-600">Year: {book.publication_year || 'N/A'}</p>
      {borrowed && (
        <p className="mt-1 text-xs font-medium text-zinc-500">
          {borrowedByCurrentUser ? 'Borrowed by you' : 'Borrowed by another user'}
        </p>
      )}
      {book.summary && <p className="mt-2 line-clamp-3 text-sm text-zinc-500">{book.summary}</p>}

      {isOwner ? (
        <div className="mt-4 space-y-2">
          <p className="rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-600">
            {borrowed ? `Borrowed by: ${borrowerLabel || 'Unknown user'}` : 'Available'}
          </p>
          <button
            className="w-full rounded-xl border border-zinc-400 bg-white px-3 py-2 text-sm font-semibold text-zinc-900"
            onClick={(event) => {
              event.stopPropagation();
              void onDelete(book.id);
            }}
            type="button"
          >
            Remove Book
          </button>
        </div>
      ) : !borrowed ? (
        <button
          className="mt-4 w-full rounded-xl bg-zinc-900 px-3 py-2 text-sm font-semibold text-white"
          onClick={(event) => {
            event.stopPropagation();
            onBorrow(book);
          }}
          type="button"
        >
          {isAuthenticated ? 'Borrow' : 'Login to Borrow'}
        </button>
      ) : (
        <button
          className={`mt-4 w-full rounded-xl border px-3 py-2 text-sm font-semibold ${
            borrowedByOtherUser
              ? 'cursor-not-allowed border-zinc-300 bg-zinc-100 text-zinc-400'
              : 'border-zinc-400 bg-white text-zinc-900'
          }`}
          onClick={(event) => {
            event.stopPropagation();
            if (borrowedByOtherUser) {
              return;
            }
            void onReturn(book.id);
          }}
          disabled={borrowedByOtherUser}
          type="button"
        >
          {borrowedByOtherUser ? 'Borrowed by Another User' : isAuthenticated ? 'Return' : 'Login to Return'}
        </button>
      )}
    </article>
  );
}
