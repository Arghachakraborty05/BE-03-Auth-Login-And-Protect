import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Header, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI security scheme for Swagger UI padlocks
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle event
    print("Server running and connected to Supabase")
    yield

app = FastAPI(
    title="Auth Service API",
    description="Authentication and protected access service (BE-03 Track: Auth - Login & Protect).",
    version="1.0.0",
    lifespan=lifespan
)

# --- Pydantic Schema for Validation ---
class UserCredentials(BaseModel):
    email: str | None = None
    password: str | None = None

@app.get("/", description="Get API information and available endpoints.")
def root():
    return {
        "name": "Auth Service API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": ["/", "/health", "/auth/signup", "/auth/login", "/public/info", "/protected/profile", "/protected/dashboard", "/auth/logout"]
    }

@app.get("/health", description="Check whether the API is running.")
def health():
    return {"status": "ok"}

# --- Stage 1: Signup Endpoint ---
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED, description="Register a new user.")
def signup(credentials: UserCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Email and password are required"}
        )
    try:
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })
        return {
            "message": "User registered successfully",
            "user": response.user
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# --- Stage 1: Login Endpoint ---
@app.post("/auth/login", description="Authenticate a user and return access and refresh tokens.")
def login(credentials: UserCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Email and password are required"}
        )
    try:
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        return {
            "message": "Login successful",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid login credentials"}
        )

# --- Stage 2: Public Endpoint ---
@app.get("/public/info", description="Public information endpoint.")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

# --- Stage 5: Reusable Auth Dependency (Swagger Bearer Integration) ---
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Access token required"}
        )

    token_parts = token.split(".")
    if len(token_parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"}
        )

    try:
        response = supabase.auth.get_user(token)

        if not response or not hasattr(response, "user") or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid or expired token"}
            )

        return response.user
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"}
        )

# --- Stage 4: Protected Profile Endpoint ---
@app.get("/protected/profile", description="Retrieve the profile of the authenticated user.")
def protected_profile(user = Depends(get_current_user)):
        return {
            "message": "Access granted - Token verified successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            }
        }

# --- Stage 4: Dashboard Endpoint ---
@app.get("/protected/dashboard", description="Retrieve user dashboard metrics and details.")
def protected_dashboard(user = Depends(get_current_user)):
    return {
        "message": "Welcome to your secure dashboard",
        "user_email": user.email,
        "metrics": {
            "active_sessions": 1,
            "account_status": "verified"
        }
    }

# --- Stage 4: Logout Endpoint ---
@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, description="Sign out the current user session.")
def logout(user = Depends(get_current_user), authorization: str | None = Header(None)):
    try:
        # Extract token and sign out the session via Supabase Auth
        token = authorization.split(" ")[1]
        supabase.auth.sign_out()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"}
        )