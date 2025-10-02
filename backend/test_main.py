from fastapi import FastAPI
from routers.recommendation import router as recommendation_router

app = FastAPI()

# Just include the recommendation router
app.include_router(recommendation_router, prefix="/api/recommendations", tags=["Recommendations"])

@app.get("/")
def root():
    return {"message": "Test server"}