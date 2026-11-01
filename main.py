import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Header
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
        "endpoints": ["/", "/health", "/auth/signup", "/auth/login"]
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
@app.get("/public/info", description="Public welcome route requiring no authentication.")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


# --- Stage 3: Strictly Verified Protected Endpoint ---
@app.get("/protected/profile", description="Protected route strictly verifying token authenticity with Supabase.")
def protected_profile(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Access token required"}
        )
    
    # Extract token string after "Bearer "
    token = authorization.split(" ")[1]
    if not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Access token required"}
        )

    # Basic structural check: A JWT must have exactly 3 parts separated by dots (header.payload.signature)
    token_parts = token.split(".")
    if len(token_parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"}
        )

    try:
        # Ask Supabase to verify the token and return the user
        response = supabase.auth.get_user(token)

        # If Supabase returns no user or data is missing, reject
        if not response or not hasattr(response, "user") or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid or expired token"}
            )

        user = response.user

        return {
            "message": "Access granted - Token verified successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        # Catch any cryptographic signature failure or network/auth error from Supabase
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"}
        )