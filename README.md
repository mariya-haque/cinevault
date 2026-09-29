# CineVault

CineVault is a small movie and file portal built with FastAPI. It has JWT authentication and two roles. Admins upload, edit, replace and delete movies or files, moderate comments and read users' chat histories. Users browse and download movies, post comments, and talk to an AI assistant (OpenAI `gpt-4o-mini`) that keeps each user's conversation in the database. The pages are server-rendered Jinja2 templates with plain JavaScript.

## Features

- Signup and login with JWT bearer tokens (HS256, valid for 60 minutes). The role (`user` or `admin`) is stored in the token.
- An admin account is created on startup from environment variables.
- **Admin dashboard**: upload movies or files (multipart), edit the title, description and genre, replace the file, delete, list all comments with the movie title, delete any comment, see which users have chatted and read their conversations, and list all users.
- **User dashboard**: list movies, view details, download files, add comments, delete your own comments, and delete your account.
- **AI assistant**: a per-user chat whose history is saved in the `chat_messages` table and sent back to the model on every turn.
- **Database**: uses `DATABASE_URL` if it is set. Otherwise it tries a local PostgreSQL database `cinevault` and falls back to SQLite (`cinevault.db`).

## Tech stack

Python, FastAPI, Uvicorn, SQLAlchemy (PostgreSQL or SQLite), python-jose (JWT), Jinja2, OpenAI API, HTML/CSS/vanilla JS.

## Project structure

```
task1/
├── main.py              # FastAPI app: pages, auth, movies, comments, chat, admin
├── database.py          # Engine selection (DATABASE_URL -> PostgreSQL -> SQLite)
├── models.py            # User, Movie, Comment, ChatMessage
├── templates/           # signup, login, user_dashboard, admin_dashboard, chatbot
├── static/
│   ├── script.js        # signup/login logic
│   ├── user.js          # user dashboard
│   ├── admin.js         # admin dashboard
│   ├── style.css
│   └── uploads/         # uploaded files (created at startup, git-ignored)
├── requirements.txt
└── .env.example
```

## Prerequisites

- Python 3.10+
- An OpenAI API key
- Optional: PostgreSQL. Without it the app uses SQLite.

## Setup

```bash
cd task1
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # then fill in the values
```

### Environment variables

| Variable | Required | Default in code | Description / where to get it |
|----------|----------|-----------------|-------------------------------|
| `OPENAI_API_KEY` | Yes (for the chatbot) | none | https://platform.openai.com/api-keys |
| `SECRET_KEY` | Strongly recommended (do not set it to an empty value) | `mysecretkey123` | Any long random string, e.g. `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | No | PostgreSQL `postgres:postgres@localhost:5432/cinevault`, then `sqlite:///./cinevault.db` | SQLAlchemy URL for your database |
| `ADMIN_USERNAME` | No | `admin` | Username of the seeded admin |
| `ADMIN_EMAIL` | No | `admin@example.com` | Email of the seeded admin |
| `ADMIN_PASSWORD` | Strongly recommended | `admin123` | Password of the seeded admin |

## Running

Run the app from inside `task1/`. The templates, static files and upload paths are relative to the working directory.

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

### Default login

On first start, an admin account is created if it does not exist yet:

| Role | Username | Password |
|------|----------|----------|
| Admin | `ADMIN_USERNAME` (default `admin`) | `ADMIN_PASSWORD` (default `admin123` when the variable is unset, `change-me` if you copied `.env.example` unchanged) |

Regular users sign up on the home page.

## Pages

| Path | Page |
|------|------|
| `/` | Signup |
| `/login` | Login |
| `/dashboard` | User dashboard (movies, comments) |
| `/chatbot` | AI assistant |
| `/admin/dashboard` | Admin dashboard |

## API

All endpoints except `/signup` and `/login` need `Authorization: Bearer <token>`.

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/signup` | public | `{ username, email, password }` |
| POST | `/login` | public | `{ username, password }`. Returns `token`, `username`, `role` |
| GET | `/profile` | user | Current user |
| POST | `/logout` | user | Clears the stored token |
| DELETE | `/delete` | user | Delete your own account |
| POST | `/chat` | user | `{ message }`. Returns the AI reply |
| GET | `/chat/history` | user | Your chat history |
| GET | `/movies` | user | List movies |
| GET | `/movies/{id}` | user | Movie details |
| GET | `/movies/{id}/download` | user | Download the file |
| GET / POST | `/movies/{id}/comments` | user | List or add comments |
| DELETE | `/comments/{id}` | owner or admin | Delete a comment |
| GET | `/users` | admin | List users |
| GET / POST | `/admin/movies` | admin | List movies, or upload one (form fields `title`, `description`, `genre`, `file`) |
| PUT | `/admin/movies/{id}` | admin | Edit metadata |
| PUT | `/admin/movies/{id}/file` | admin | Replace the file |
| DELETE | `/admin/movies/{id}` | admin | Delete a movie and its comments |
| GET | `/admin/comments` | admin | All comments |
| GET | `/admin/chats` | admin | Users who have chat history |
| GET | `/admin/chats/{username}` | admin | One user's conversation |

Interactive docs: http://127.0.0.1:8000/docs

## Known limitations

- Passwords are stored and compared in plain text. Do not use real credentials.
- Uploaded files are saved under `static/uploads/`, which is served publicly at `/static/uploads/<stored name>` without authentication.
- After you delete your account, the frontend redirects to `/signup`, which has no route. The signup page is at `/`.
