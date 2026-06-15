from src.common.errors import bad_request, conflict, unauthorized

from src.core.security import create_access_token, hash_password, verify_password
from src.modules.auth.models import User
from src.modules.auth.repository import AuthRepository
from src.modules.auth.schemas import UserLogin, UserProfileUpdate, UserRegister


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    def register(self, payload: UserRegister) -> User:
        if self.repository.get_by_email(payload.email):
            raise conflict(
                f"User with email {payload.email} already exists",
                error_code="EMAIL_ALREADY_EXISTS",
                resource="user",
            )
        if payload.program_id is None or payload.current_level is None:
            raise bad_request(
                "program_id and current_level are required for student registration",
                error_code="STUDENT_PROFILE_FIELDS_REQUIRED",
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
            raise unauthorized("Invalid email or password", error_code="INVALID_CREDENTIALS")
        return create_access_token(str(user.id))

    def update_profile(self, user: User, payload: UserProfileUpdate) -> User:
        user.program_id = payload.program_id
        user.current_level = payload.current_level
        user.profile_update_required = False
        return self.repository.save(user)
