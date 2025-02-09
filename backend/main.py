from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health_plans, calculate, recommend
from routers.calculate import router as calculate_router

app = FastAPI()

# Routers
app.include_router(health_plans.router, prefix="/api/health-plans", tags=["Health Plans"])
app.include_router(calculate.router, prefix="/api/calculate", tags=["Calculate"])
app.include_router(recommend.router, prefix="/api/recommend", tags=["Recommend"])
app.include_router(calculate_router, prefix="/api")

# Test route to check application health
@app.get("/ping")
def ping():
    return {"message": "Application is running!"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],# ["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],# ["*", "GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],# ["*", "Content-Type", "Authorization"],
)

@app.options("/{path:path}")
async def options_handler(path: str):
    return {}