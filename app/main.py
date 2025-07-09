from fastapi import FastAPI
from app.user import router as user_router
from app.admin import router as admin_router

app = FastAPI()

app.include_router(user_router, prefix="/user")
app.include_router(admin_router, prefix="/admin") 