import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
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

@app.get("/", description="Get API information and available endpoints.")
def root():
    return {
        "name": "Auth Service API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": ["/", "/health", "/signup", "/login"]
    }

@app.get("/health", description="Check whether the API is running.")
def health():
    return {"status": "ok"}