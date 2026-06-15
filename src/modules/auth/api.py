from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.common.errors import forbidden, unauthorized
from src.core.config import settings
from src.core.prototype import ensure_prototype_user_with_prerequisites
from src.core.security import decode_access_token
from src.db.session import get_db
from src.modules.auth.models import User
from src.modules.auth.repository import AuthRepository
from src.modules.auth.schemas import TokenResponse, UserLogin, UserProfileUpdate, UserRead, UserRegister
from src.modules.auth.service import AuthService

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(AuthRepository(db))


def get_current_user(
    db: Session = Depends(get_db), token: str | None = Depends(oauth2_scheme)
) -> User:
    if settings.PROTOTYPE_MODE:
        return ensure_prototype_user_with_prerequisites(
            db,
            user_id=settings.PROTOTYPE_USER_ID,
            role=settings.PROTOTYPE_USER_ROLE,
        )

    if not token:
        raise unauthorized("Authentication token was not provided", error_code="TOKEN_MISSING")
    subject = decode_access_token(token)
    if subject is None:
        raise unauthorized("Authentication token is invalid or expired", error_code="TOKEN_INVALID")
    user = AuthRepository(db).get_by_id(int(subject))
    if user is None:
        raise unauthorized("Authenticated user could not be found", error_code="AUTH_USER_NOT_FOUND", resource="user")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if settings.PROTOTYPE_MODE:
        return current_user
    if current_user.role != "admin":
        raise forbidden("Admin access is required for this operation", error_code="ADMIN_REQUIRED")
    return current_user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, service: AuthService = Depends(get_auth_service)):
    return service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, service: AuthService = Depends(get_auth_service)):
    token = service.login(payload)
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
async def token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    token = service.login(UserLogin(email=form_data.username, password=form_data.password))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/profile", response_model=UserRead)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    return service.update_profile(current_user, payload)
