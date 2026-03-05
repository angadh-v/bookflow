export type BookStatus = 'available' | 'borrowed';

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn?: string;
  publication_year?: number;
  genre?: string;
  image_url?: string;
  summary?: string;
  status: BookStatus;
  borrowed_by?: number;
  borrowed_by_auth0_id?: string;
  borrowed_by_email?: string;
  borrowed_at?: string;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatPayload {
  reply: string;
  books?: Book[];
}
