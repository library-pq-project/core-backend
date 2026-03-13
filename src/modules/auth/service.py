from fastapi import HTTPException, status

from src.core.security import create_access_token, hash_password, verify_password
from src.modules.auth.models import User
from src.modules.auth.repository import AuthRepository
from src.modules.auth.schemas import UserLogin, UserProfileUpdate, UserRegister


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    def register(self, payload: UserRegister) -> User:
        if self.repository.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        if payload.program_id is None or payload.current_level is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="program_id and current_level are required for student registration",
            )

        user = User(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="student",
            program_id=payload.program_id,
            current_level=payload.current_level,
        )
        return self.repository.create(user)

    def login(self, payload: UserLogin) -> str:
        user = self.repository.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return create_access_token(str(user.id))

    def update_profile(self, user: User, payload: UserProfileUpdate) -> User:
        user.program_id = payload.program_id
        user.current_level = payload.current_level
        user.profile_update_required = False
        return self.repository.save(user)
