from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import forecast, inventory

app = FastAPI(
    title="Demand Planning API",
    description="API for demand planning and inventory management",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(forecast.router)
app.include_router(inventory.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Demand Planning API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 