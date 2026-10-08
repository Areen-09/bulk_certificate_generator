from fastapi import APIRouter

from app.api.v1.endpoints.certificates import router as certificates_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.verify import router as verify_router

api_router = APIRouter()

api_router.include_router(jobs_router)
api_router.include_router(certificates_router)
api_router.include_router(verify_router)
