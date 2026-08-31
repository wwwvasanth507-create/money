from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.wallet import router as wallet_router
from app.api.v1.deposit_desk import router as deposit_desk_router
from app.api.v1.games import router as games_router
from app.api.v1.kyc import router as kyc_router
from app.api.v1.responsible_gaming import router as rg_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter(prefix="/v1")

api_router.include_router(auth_router)
api_router.include_router(wallet_router)
api_router.include_router(deposit_desk_router)
api_router.include_router(games_router)
api_router.include_router(kyc_router)
api_router.include_router(rg_router)
api_router.include_router(admin_router)
