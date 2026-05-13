from datetime import datetime, timedelta, timezone
import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:

    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()   
    hashed = bcrypt.hashpw(pwd_bytes, salt)
 
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
   pwd_bytes = plain_password.encode('utf-8')[:72]
   hash_bytes = hashed_password.encode('utf-8')
    
   try:
      return bcrypt.checkpw(pwd_bytes, hash_bytes)
   except ValueError:
      return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
