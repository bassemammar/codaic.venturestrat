"""VentureStrat Forge — API v1 router."""

from fastapi import APIRouter

from api.v1.requirements import router as requirements_router
from api.v1.execution import router as execution_router
from api.v1.admin import router as admin_router
from api.v1.feedback import router as feedback_router

router = APIRouter()

router.include_router(requirements_router, prefix='/requirements', tags=['requirements'])
router.include_router(execution_router, prefix='/execution', tags=['execution'])
router.include_router(admin_router, prefix='/admin', tags=['admin'])
router.include_router(feedback_router, prefix='/feedback', tags=['feedback'])
