'use client';

import { useState } from 'react';

import { chatWithLibrarian } from '@/lib/api';
import { Book } from '@/lib/types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  books?: Book[];
}

interface ChatInterfaceProps {
  className?: string;
  title?: string;
  hideTitle?: boolean;
}

export default function ChatInterface({ className = '', title = 'AI Assistant', hideTitle = false }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!prompt.trim()) {
      return;
    }

    const userMessage: Message = { role: 'user', content: prompt.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setPrompt('');
    setLoading(true);
    setError(null);

    try {
      const response = await chatWithLibrarian(userMessage.content);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.reply,
          books: response.books
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to contact AI librarian');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={`rounded-2xl border border-zinc-300 bg-white p-4 ${className}`}>
      {!hideTitle && <h2 className="mb-3 text-lg font-bold text-zinc-900">{title}</h2>}
      <div className="mb-4 max-h-[50vh] space-y-3 overflow-auto rounded-xl border border-zinc-200 bg-zinc-50 p-3">
        {messages.length === 0 && (
          <p className="text-sm text-zinc-500">Try: &quot;Books for young adults&quot;</p>
        )}
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`rounded-lg px-3 py-2 text-sm ${
              message.role === 'user' ? 'ml-8 bg-zinc-900 text-white' : 'mr-8 bg-white text-zinc-900'
            }`}
          >
            <p>{message.content}</p>
            {message.books && message.books.length > 0 && (
              <ul className="mt-2 list-disc pl-5">
                {message.books.slice(0, 5).map((book) => (
                  <li key={book.id}>
                    {book.title} by {book.author} ({book.status})
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {error && <p className="mb-3 text-sm font-medium text-red-700">{error}</p>}
      <form className="flex gap-2" onSubmit={send}>
        <input
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Ask about books..."
          className="w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-zinc-900"
          disabled={loading}
        />
        <button
          disabled={loading}
          className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          type="submit"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  );
}
