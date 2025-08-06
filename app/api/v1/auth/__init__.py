from fastapi import APIRouter

from .auth import router as auth_router
from .register import router as register_router
from .password import router as password_router

router_auth = APIRouter()
router_auth.include_router(auth_router)
router_auth.include_router(register_router)
router_auth.include_router(password_router)
