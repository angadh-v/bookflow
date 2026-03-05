# BookFlow - Library Management System

Full-stack library management app with role-based permissions, borrowing workflows, and AI-powered features.

## Features

### Catalogue and Discovery
- Public catalogue browsing (guests can view books without logging in)
- Search across title, author, genre, and summary
- Book cards with cover image, status, genre, year, and summary preview

### Borrowing Workflow
- Borrow request with pickup location and pickup time selection
- Clear UI states for borrowed-by-you vs borrowed-by-another-user

### Auth and Permissions
- Auth0 login/logout via Next.js Auth0 routes
- Backend JWT validation against Auth0 JWKS with audience/issuer checks
- Three effective access levels:
  - Guest: browse catalogue only
  - Client: borrow and return own books
  - Owner: add/remove books and run metadata enrichment
  
### AI Features
- AI search assistant with deterministic fallback when model/provider is unavailable
- Owner-only AI metadata enrichment with OpenLibrary fallback for missing fields:
  - genre
  - summary
  - publication year
  - cover image 

### Data and API
- Book CRUD endpoints (owner-restricted for create/update/delete)
- Borrow/check-in endpoints with transactional checks
- Chat endpoint for assistant queries
- Health endpoint for uptime checks
- Auto schema compatibility checks for newly added metadata columns

## Tech Stack

- Backend: FastAPI, SQLAlchemy, MySQL/SQLite, Pydantic, LangChain/OpenAI-compatible providers
- Frontend: Next.js 14, TypeScript, Tailwind CSS, Auth0 Next.js SDK
- Auth: Auth0
- AI providers: OpenAI-compatible APIs (OpenAI/OpenRouter)
- Deployment targets: Render (backend), Vercel (frontend), Aiven (MySQL)
