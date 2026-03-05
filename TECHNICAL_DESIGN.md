# Library Management System - Corrected Technical Design

## 1. Overview

A full-stack library management system with:
- Book CRUD operations
- Check-in/check-out tracking
- Multi-field search
- Auth0-backed authentication and authorization
- AI-assisted natural language search over catalog data

## 2. Architecture

### Backend
- Framework: FastAPI
- ORM: SQLAlchemy 2.x
- Database: MySQL in production, SQLite for local tests
- Auth: Auth0 JWT validation (RS256, JWKS)
- AI: OpenAI via LangChain (optional feature flag)

### Frontend
- Framework: Next.js 14 + TypeScript
- Styling: Tailwind CSS
- Auth: `@auth0/nextjs-auth0`
- API integration: BFF proxy route in Next.js to inject bearer token server-side

### Deployment
- Backend: Render
- Frontend: Vercel
- Database: Aiven MySQL

## 3. Data Model

```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  auth0_id VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_users_auth0_id (auth0_id)
);

CREATE TABLE books (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  author VARCHAR(255) NOT NULL,
  isbn VARCHAR(20) UNIQUE,
  publication_year INT,
  genre VARCHAR(100),
  status ENUM('available', 'borrowed') NOT NULL DEFAULT 'available',
  borrowed_by INT NULL,
  borrowed_at TIMESTAMP NULL,
  due_date DATE NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_publication_year CHECK (publication_year IS NULL OR publication_year BETWEEN 1000 AND 2100),
  CONSTRAINT fk_books_borrowed_by FOREIGN KEY (borrowed_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_books_title (title),
  INDEX idx_books_author (author),
  INDEX idx_books_genre (genre),
  INDEX idx_books_status (status)
);
```

## 4. API Design

Base path: `/api`

### Health
- `GET /health`

### Books
- `GET /books` list with pagination (`skip`, `limit` with max cap)
- `GET /books/search` multi-field search (declared before `/{book_id}` route)
- `GET /books/{book_id}`
- `POST /books` (auth required)
- `PUT /books/{book_id}` (auth required)
- `DELETE /books/{book_id}` (auth required)
- `POST /books/{book_id}/checkout` (auth required)
- `POST /books/{book_id}/checkin` (auth required)

### AI
- `POST /chat` (auth required)

## 5. Authentication Strategy

### Backend
- Parse bearer token from `Authorization` header
- Resolve signing key from JWKS endpoint
- Validate `alg`, `aud`, and `iss`
- Create-or-load local user record by `sub`

### Frontend (corrected)
- Do not fetch backend directly from browser with SDK-only token APIs that are not available in App Router client hooks.
- Use a Next.js BFF route (`/api/library/[...path]`) that:
  1. reads session/access token server-side
  2. forwards request to FastAPI backend
  3. returns normalized response/errors

## 6. AI Service Design

- AI feature is optional and controlled by `AI_ENABLED`
- Natural-language query is converted to search filters
- Query backend DB with bounded limit
- Return both:
  - conversational `reply`
  - structured `books` list with required response fields
- If AI provider fails, return deterministic fallback search guidance

## 7. Reliability & Security

- SQLAlchemy ORM for parameterized queries
- CORS restricted by environment variable allowlist
- Request timeouts for JWKS HTTP requests
- Pagination limit capped (e.g., 100)
- Transactional checkout/checkin with row locking (`SELECT ... FOR UPDATE` where supported)
- Centralized error formatting on frontend proxy

## 8. Project Layout

```text
backend/
  app/
    api/
      books.py
      chat.py
    auth/
      dependencies.py
    services/
      ai_service.py
    config.py
    database.py
    main.py
    models.py
    schemas.py
  tests/
    test_books_api.py

frontend/
  app/
    api/auth/[auth0]/route.ts
    api/library/[...path]/route.ts
    dashboard/page.tsx
    chat/page.tsx
    page.tsx
    layout.tsx
  components/
    BookCard.tsx
    SearchBar.tsx
    ChatInterface.tsx
  lib/
    api.ts
    types.ts
```

## 9. Environment Variables

### Backend
- `DATABASE_URL`
- `CORS_ORIGINS`
- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AI_ENABLED`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

### Frontend
- `BACKEND_API_URL`
- `AUTH0_SECRET`
- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_AUDIENCE`
- `APP_BASE_URL`

## 10. Acceptance Criteria

- CRUD/search/checkin/checkout work and persist correctly
- Protected endpoints reject missing/invalid tokens
- Search route is reachable and not shadowed by dynamic ID route
- AI endpoint returns stable schema (`reply`, `books`)
- Frontend can list and search books through BFF proxy without leaking backend token handling to client code
