# ResolveZA

ResolveZA is a full-stack telecom dispute resolution platform with a FastAPI backend and a Next.js frontend.

## Stack

- Backend: FastAPI, SQLAlchemy, SQL Server, Redis, JWT auth
- Frontend: Next.js 16, React 19, TypeScript, App Router, CSS Modules
- Local infra: Docker for SQL Server, Redis, backend, and frontend

## Repository Layout

```text
ResolveZA/
  Backend/
  Frontend/
```

## Features

- JWT-based staff authentication
- Protected frontend routes for authenticated users
- Customer, ticket, and refund workflows in the backend
- Protected dashboard shell with sidebar navigation, current-user state, and logout
- Live overview, customers, tickets, and refunds pages backed by real API data
- Typed frontend dashboard data layer for users, customers, accounts, transactions, tickets, and refunds
- Security hardening in the backend API layer
- TypeScript frontend API client wired to the backend

## Prerequisites

- Python 3.12
- Node.js 20+
- Docker Desktop

## Local Ports

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- SQL Server: `localhost:1433`
- Redis: `localhost:6379`

## Fastest Start

To run the full stack with Docker:

```powershell
docker compose up --build -d
```

This starts:

- `frontend` at `http://localhost:3000`
- `backend` at `http://localhost:8000`
- `sqlserver` at `localhost:1433`
- `redis` at `localhost:6379`

After the stack is up:

- open `http://localhost:3000`
- unauthenticated requests are redirected to `http://localhost:3000/login`
- sign in with one of the seeded staff accounts below

## Backend Setup

### 1. Install Python dependencies

From `Backend/`:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure backend env

Primary local env file:

- [`Backend/.env`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Backend/.env)

Docker-backed local backend env:

- [`Backend/.env.dockerlocal`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Backend/.env.dockerlocal)

### 3. Start infrastructure

SQL Server:

```powershell
docker run -d --name resolveza-sql `
  -e ACCEPT_EULA=Y `
  -e SA_PASSWORD=DevPassword123! `
  -p 1433:1433 `
  mcr.microsoft.com/mssql/server:2022-latest
```

Redis:

```powershell
docker run -d --name resolveza-redis -p 6379:6379 redis:7-alpine
```

### 4. Run the backend

From `Backend/`:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or run the backend Docker image:

```powershell
docker build -t resolveza-backend Backend
docker run -d --name resolveza-backend-local -p 8000:8000 --env-file Backend/.env.dockerlocal resolveza-backend
```

Backend Docker support files:

- [`Backend/Dockerfile`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Backend/Dockerfile)
- [`Backend/.dockerignore`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Backend/.dockerignore)

### 5. Seed the database

The backend CLI supports:

- `create-admin`
- `seed`
- `reset-db --confirm --seed`

From `Backend/`:

```powershell
.\venv\Scripts\python.exe -c "import sys; from app.cli import main; sys.argv=['app.cli','reset-db','--confirm','--seed']; main()"
```

## Frontend Setup

### 1. Install dependencies

From `Frontend/`:

```powershell
npm install
```

### 2. Configure frontend env

The frontend uses:

- [`Frontend/.env.local`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/.env.local)

Current API target:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run the frontend

From `Frontend/`:

```powershell
npm run dev
```

The frontend shell includes:

- `/dashboard` for overview metrics and recent queue activity
- `/customers` for customer, account, transaction, ticket, and refund relationships
- `/tickets` for ticket detail, message history, and status updates
- `/refunds` for refund review with linked ticket, customer, and transaction context

Or run the frontend Docker image:

```powershell
docker build -t resolveza-frontend Frontend
docker run -p 3000:3000 resolveza-frontend
```

Frontend Docker support files:

- [`Frontend/Dockerfile`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/Dockerfile)
- [`Frontend/.dockerignore`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/.dockerignore)

## Demo Login Credentials

Seeded accounts:

- `admin@resolveza.co.za` / `Admin@123!`
- `supervisor@resolveza.co.za` / `Super@123!`
- `agent1@resolveza.co.za` / `Agent@123!`
- `agent2@resolveza.co.za` / `Agent@123!`

Login page:

- `http://localhost:3000/login`

Primary frontend dashboard files:

- [`Frontend/lib/dashboard.ts`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/lib/dashboard.ts)
- [`Frontend/lib/dashboard-session.tsx`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/lib/dashboard-session.tsx)
- [`Frontend/app/(dashboard)/layout.tsx`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/app/(dashboard)/layout.tsx)

## Verification

Full stack compose validation:

```powershell
docker compose config
```

Backend health:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health/ready
```

Frontend build:

```powershell
cd Frontend
npm run build
```

To rebuild and restart the full stack after frontend changes:

```powershell
docker compose up --build -d
docker compose ps
```

Backend tests:

```powershell
cd Backend
.\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

## Auth Flow

- Frontend stores access and refresh tokens in `localStorage`
- Frontend also sets a lightweight `rzauth=1` cookie for route protection
- Protected routes are enforced in [`Frontend/proxy.ts`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/proxy.ts)
- Frontend API calls are handled through [`Frontend/lib/api.ts`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/Frontend/lib/api.ts)

## Notes

- The backend Docker image includes ODBC Driver 18 for SQL Server support.
- The frontend is TypeScript-based and uses CSS Modules only.
- The frontend is containerized with a multi-stage production build.
- The full stack compose definition lives in [`docker-compose.yml`](/c:/Users/khany/The-Shard-Interview-Projects-Khanyisa/ResolveZA/docker-compose.yml).
- Route groups exist for:
  - `(auth)`
  - `(dashboard)`
