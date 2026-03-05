import { Book, ChatPayload } from '@/lib/types';

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const message = data?.detail || data?.message || `Request failed (${res.status})`;
    throw new Error(message);
  }

  return data as T;
}

export async function getBooks(): Promise<Book[]> {
  const res = await fetch('/api/library/books', { cache: 'no-store' });
  return parseJson<Book[]>(res);
}

export async function searchBooks(query: string): Promise<Book[]> {
  const res = await fetch(`/api/library/books/search?q=${encodeURIComponent(query)}`, {
    cache: 'no-store'
  });
  return parseJson<Book[]>(res);
}

export async function createBook(payload: Partial<Book>): Promise<Book> {
  const res = await fetch('/api/library/books', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return parseJson<Book>(res);
}

export async function deleteBook(bookId: number): Promise<void> {
  const res = await fetch(`/api/library/books/${bookId}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    const message = data?.detail || data?.message || `Request failed (${res.status})`;
    throw new Error(message);
  }
}

export async function checkoutBook(bookId: number): Promise<Book> {
  const res = await fetch(`/api/library/books/${bookId}/checkout`, { method: 'POST' });
  return parseJson<Book>(res);
}

export async function checkinBook(bookId: number): Promise<Book> {
  const res = await fetch(`/api/library/books/${bookId}/checkin`, { method: 'POST' });
  return parseJson<Book>(res);
}

export async function enrichBook(bookId: number): Promise<Book> {
  const res = await fetch(`/api/library/books/${bookId}/enrich`, { method: 'POST' });
  return parseJson<Book>(res);
}

export async function chatWithLibrarian(message: string): Promise<ChatPayload> {
  const res = await fetch('/api/library/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  return parseJson<ChatPayload>(res);
}
