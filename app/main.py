from fastapi import FastAPI

from app.routers.users import router as users_router
from app.routers.orders import router as order_router

app = FastAPI()

app.include_router(users_router)
app.include_router(order_router)