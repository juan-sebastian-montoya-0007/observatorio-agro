from fastapi import APIRouter

from app.api.v1.agriculture import router as agriculture_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.exports import router as exports_router
from app.api.v1.geography import router as geography_router

api_router = APIRouter()
api_router.include_router(agriculture_router)
api_router.include_router(catalog_router)
api_router.include_router(exports_router)
api_router.include_router(geography_router)
