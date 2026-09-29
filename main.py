from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import os
import shutil
import uuid
from openai import OpenAI
from dotenv import load_dotenv

from database import engine, Base, get_db
from models import User as UserModel, Movie as MovieModel, Comment as CommentModel, ChatMessage as ChatMessageModel

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# ==========================
# App Configuration
# ==========================

app = FastAPI(title="FastAPI JWT Authentication + Movie Portal (PostgreSQL)")

SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey123")
ALGORITHM = "HS256"

UPLOAD_DIR = "static/uploads"

# Seed admin credentials (change these via .env in production)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

security = HTTPBearer()

templates = Jinja2Templates(directory="templates")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Tables ban jayengi agar pehle se nahi hain
Base.metadata.create_all(bind=engine)


# ==========================
# Seed default admin account
# ==========================

def seed_admin():

    db = next(get_db())

    try:
        existing = db.query(UserModel).filter(UserModel.username == ADMIN_USERNAME).first()

        if existing:
            return

        admin = UserModel(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            role="admin",
            token=""
        )

        db.add(admin)
        db.commit()

    finally:
        db.close()


seed_admin()


# ==========================
# Models (request/response schemas)
# ==========================

class Signup(BaseModel):
    username: str
    email: EmailStr
    password: str


class Login(BaseModel):
    username: str
    password: str


class ChatMessageIn(BaseModel):
    message: str


class MovieUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    genre: str | None = None


class CommentCreate(BaseModel):
    text: str


# ==========================
# Serialization Helpers
# ==========================

def movie_to_dict(m: MovieModel):
    return {
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "genre": m.genre,
        "original_filename": m.original_filename,
        "stored_filename": m.stored_filename,
        "uploaded_by": m.uploaded_by,
        "uploaded_at": m.uploaded_at.isoformat()
    }


def comment_to_dict(c: CommentModel):
    return {
        "id": c.id,
        "movie_id": c.movie_id,
        "username": c.username,
        "text": c.text,
        "created_at": c.created_at.isoformat()
    }


# ==========================
# JWT Functions
# ==========================

def create_token(username: str, role: str):

    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=60)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(
        credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role", "user")

        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid Token"
            )

        return {"username": username, "role": role}

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid Token"
        )


def require_admin(current=Depends(verify_token)):

    if current["role"] != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current


# ==========================
# Templates / Pages
# ==========================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="signup.html"
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.get("/chatbot", response_class=HTMLResponse)
def chatbot_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="chatbot.html"
    )


@app.get("/dashboard", response_class=HTMLResponse)
def user_dashboard_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="user_dashboard.html"
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html"
    )


# ==========================
# SIGNUP  (always creates a normal "user")
# ==========================

@app.post("/signup")
def signup(user: Signup, db: Session = Depends(get_db)):

    if db.query(UserModel).filter(UserModel.username == user.username).first():

        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    if db.query(UserModel).filter(UserModel.email == user.email).first():

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    new_user = UserModel(
        username=user.username,
        email=user.email,
        password=user.password,
        role="user",
        token=""
    )

    db.add(new_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")

    return {
        "message": "Signup Successful"
    }


# ==========================
# LOGIN
# ==========================

@app.post("/login")
def login(user: Login, db: Session = Depends(get_db)):

    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()

    if not db_user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if db_user.password != user.password:

        raise HTTPException(
            status_code=400,
            detail="Incorrect Password"
        )

    token = create_token(db_user.username, db_user.role)

    db_user.token = token
    db.commit()

    return {
        "message": "Login Successful",
        "token": token,
        "username": db_user.username,
        "role": db_user.role
    }


# ==========================
# PROFILE
# ==========================

@app.get("/profile")
def profile(current=Depends(verify_token), db: Session = Depends(get_db)):

    db_user = db.query(UserModel).filter(UserModel.username == current["username"]).first()

    if not db_user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role
    }


# ==========================
# CHATBOT
# ==========================

@app.post("/chat")
def chatbot(
    data: ChatMessageIn,
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):

    username = current["username"]

    has_history = db.query(ChatMessageModel).filter(
        ChatMessageModel.username == username
    ).first()

    if not has_history:

        db.add(
            ChatMessageModel(
                username=username,
                role="system",
                content=(
                    f"You are a friendly AI assistant. "
                    f"The user's name is {username}. "
                    "Always remember the user's name during this conversation. "
                    "Answer every question clearly and professionally."
                )
            )
        )

    db.add(
        ChatMessageModel(
            username=username,
            role="user",
            content=data.message
        )
    )

    db.commit()

    history = db.query(ChatMessageModel).filter(
        ChatMessageModel.username == username
    ).order_by(ChatMessageModel.id).all()

    input_messages = [{"role": m.role, "content": m.content} for m in history]

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=input_messages
        )

        answer = response.choices[0].message.content

        db.add(
            ChatMessageModel(
                username=username,
                role="assistant",
                content=answer
            )
        )

        db.commit()

        return {
            "user": username,
            "response": answer
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/chat/history")
def get_chat_history(
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):

    username = current["username"]

    messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.username == username,
        ChatMessageModel.role != "system"
    ).order_by(ChatMessageModel.id).all()

    return [
        {"role": m.role, "content": m.content}
        for m in messages
    ]


# ==========================
# GET USERS
# ==========================

@app.get("/users")
def get_users(current=Depends(require_admin), db: Session = Depends(get_db)):

    users = db.query(UserModel).all()

    return [
        {
            "username": u.username,
            "email": u.email,
            "role": u.role
        }
        for u in users
    ]


# ==========================
# DELETE ACCOUNT
# ==========================

@app.delete("/delete")
def delete_account(
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):

    db_user = db.query(UserModel).filter(UserModel.username == current["username"]).first()

    if db_user:
        db.delete(db_user)
        db.commit()

    return {
        "message": "Account Deleted Successfully"
    }


# ==========================
# LOGOUT
# ==========================

@app.post("/logout")
def logout(
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):

    db_user = db.query(UserModel).filter(UserModel.username == current["username"]).first()

    if db_user:
        db_user.token = ""
        db.commit()

    return {
        "message": "Logout Successful"
    }


# ==========================================================
# MOVIE / FILE PORTAL
# ==========================================================

# --------------------------
# ADMIN: Upload a movie/file
# --------------------------

@app.post("/admin/movies")
def upload_movie(
    title: str = Form(...),
    description: str = Form(""),
    genre: str = Form(""),
    file: UploadFile = File(...),
    current=Depends(require_admin),
    db: Session = Depends(get_db)
):

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(stored_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_movie = MovieModel(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        genre=genre,
        original_filename=file.filename,
        stored_filename=stored_name,
        uploaded_by=current["username"]
    )

    db.add(new_movie)
    db.commit()

    return {
        "message": "Movie uploaded successfully",
        "id": new_movie.id
    }


# --------------------------
# ADMIN: List all movies (full detail)
# --------------------------

@app.get("/admin/movies")
def admin_list_movies(current=Depends(require_admin), db: Session = Depends(get_db)):

    movies = db.query(MovieModel).order_by(MovieModel.uploaded_at.desc()).all()

    return [movie_to_dict(m) for m in movies]


# --------------------------
# ADMIN: Edit movie metadata
# --------------------------

@app.put("/admin/movies/{movie_id}")
def edit_movie(
    movie_id: str,
    update: MovieUpdate,
    current=Depends(require_admin),
    db: Session = Depends(get_db)
):

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    if update.title is not None:
        movie.title = update.title

    if update.description is not None:
        movie.description = update.description

    if update.genre is not None:
        movie.genre = update.genre

    db.commit()

    return {
        "message": "Movie updated successfully",
        "movie": movie_to_dict(movie)
    }


# --------------------------
# ADMIN: Replace the uploaded file itself
# --------------------------

@app.put("/admin/movies/{movie_id}/file")
def replace_movie_file(
    movie_id: str,
    file: UploadFile = File(...),
    current=Depends(require_admin),
    db: Session = Depends(get_db)
):

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    old_path = os.path.join(UPLOAD_DIR, movie.stored_filename)

    if os.path.exists(old_path):
        os.remove(old_path)

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(stored_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    movie.stored_filename = stored_name
    movie.original_filename = file.filename

    db.commit()

    return {
        "message": "File replaced successfully"
    }


# --------------------------
# ADMIN: Delete a movie/file
# --------------------------

@app.delete("/admin/movies/{movie_id}")
def delete_movie(
    movie_id: str,
    current=Depends(require_admin),
    db: Session = Depends(get_db)
):

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    file_path = os.path.join(UPLOAD_DIR, movie.stored_filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    # Comments bhi khud delete ho jayenge (cascade relationship)
    db.delete(movie)
    db.commit()

    return {
        "message": "Movie deleted successfully"
    }


# --------------------------
# USER + ADMIN: List available movies (public list, no upload path leaked)
# --------------------------

@app.get("/movies")
def list_movies(current=Depends(verify_token), db: Session = Depends(get_db)):

    movies = db.query(MovieModel).order_by(MovieModel.uploaded_at.desc()).all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "genre": m.genre,
            "uploaded_at": m.uploaded_at.isoformat()
        }
        for m in movies
    ]


# --------------------------
# USER + ADMIN: Movie details
# --------------------------

@app.get("/movies/{movie_id}")
def movie_details(movie_id: str, current=Depends(verify_token), db: Session = Depends(get_db)):

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    return {
        "id": movie.id,
        "title": movie.title,
        "description": movie.description,
        "genre": movie.genre,
        "original_filename": movie.original_filename,
        "uploaded_at": movie.uploaded_at.isoformat()
    }


# --------------------------
# USER + ADMIN: Download a movie/file
# --------------------------

@app.get("/movies/{movie_id}/download")
def download_movie(movie_id: str, current=Depends(verify_token), db: Session = Depends(get_db)):

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    file_path = os.path.join(UPLOAD_DIR, movie.stored_filename)

    if not os.path.exists(file_path):

        raise HTTPException(
            status_code=404,
            detail="File missing on server"
        )

    return FileResponse(
        path=file_path,
        filename=movie.original_filename,
        media_type="application/octet-stream"
    )


# ==========================================================
# COMMENTS  (any logged-in user can post/read; owner or admin can delete)
# ==========================================================

@app.post("/movies/{movie_id}/comments")
def add_comment(
    movie_id: str,
    comment: CommentCreate,
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    if not comment.text.strip():

        raise HTTPException(
            status_code=400,
            detail="Comment can't be empty"
        )

    new_comment = CommentModel(
        id=str(uuid.uuid4()),
        movie_id=movie_id,
        username=current["username"],
        text=comment.text.strip()
    )

    db.add(new_comment)
    db.commit()

    return comment_to_dict(new_comment)


@app.get("/movies/{movie_id}/comments")
def get_movie_comments(movie_id: str, current=Depends(verify_token), db: Session = Depends(get_db)):

    comments = db.query(CommentModel).filter(
        CommentModel.movie_id == movie_id
    ).order_by(CommentModel.created_at).all()

    return [comment_to_dict(c) for c in comments]


@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: str, current=Depends(verify_token), db: Session = Depends(get_db)):

    comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()

    if not comment:

        raise HTTPException(
            status_code=404,
            detail="Comment not found"
        )

    if current["role"] != "admin" and comment.username != current["username"]:

        raise HTTPException(
            status_code=403,
            detail="You can only delete your own comments"
        )

    db.delete(comment)
    db.commit()

    return {
        "message": "Comment deleted successfully"
    }


@app.get("/admin/comments")
def admin_list_comments(current=Depends(require_admin), db: Session = Depends(get_db)):

    comments = db.query(CommentModel).order_by(CommentModel.created_at.desc()).all()

    result = []

    for c in comments:
        movie = db.query(MovieModel).filter(MovieModel.id == c.movie_id).first()
        result.append({
            **comment_to_dict(c),
            "movie_title": movie.title if movie else "Unknown"
        })

    return result


# ==========================================================
# ADMIN: VIEW USER CHAT HISTORY
# ==========================================================

@app.get("/admin/chats")
def admin_list_chats(current=Depends(require_admin), db: Session = Depends(get_db)):

    usernames = [row[0] for row in db.query(ChatMessageModel.username).distinct().all()]

    result = []

    for username in usernames:

        count = db.query(ChatMessageModel).filter(
            ChatMessageModel.username == username,
            ChatMessageModel.role != "system"
        ).count()

        result.append({
            "username": username,
            "message_count": count
        })

    return result


@app.get("/admin/chats/{username}")
def admin_get_chat(username: str, current=Depends(require_admin), db: Session = Depends(get_db)):

    any_message = db.query(ChatMessageModel).filter(
        ChatMessageModel.username == username
    ).first()

    if not any_message:

        raise HTTPException(
            status_code=404,
            detail="No chat history for this user"
        )

    messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.username == username,
        ChatMessageModel.role != "system"
    ).order_by(ChatMessageModel.id).all()

    return {
        "username": username,
        "messages": [{"role": m.role, "content": m.content} for m in messages]
    }
