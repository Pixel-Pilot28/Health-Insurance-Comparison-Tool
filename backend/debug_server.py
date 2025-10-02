#!/usr/bin/env python3
"""
Simple FastAPI server to debug recommendations API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os

# Import routers  
from routers.recommendation import router as recommendation_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add recommendation router
app.include_router(recommendation_router, prefix="/api/recommendations", tags=["Recommendations"])

@app.get("/")
def root():
    return {"message": "Debug Recommendation Server Running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "debug": True}

if __name__ == "__main__":
    print("Starting debug recommendation server on port 8000...")
    print("Debug output will appear in this terminal...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")