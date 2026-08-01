from typing import Any, AsyncGenerator, Optional

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.exceptions import InvalidPasswordException
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db.base import BaseUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_async_session
from .models import User

USER_ID = int


class UserDatabase(BaseUserDatabase[User, USER_ID]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: USER_ID) -> Optional[User]:
        return await self.session.get(User, id)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_oauth_account(
        self, oauth: str, account_id: str
    ) -> Optional[User]:
        raise NotImplementedError("OAuth not yet supported")

    async def create(self, create_dict: dict) -> User:
        user = User(**create_dict)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, update_dict: dict) -> User:
        for key, value in update_dict.items():
            setattr(user, key, value)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()

    async def add_oauth_account(
        self, user: User, create_dict: dict
    ) -> User:
        raise NotImplementedError("OAuth not yet supported")

    async def update_oauth_account(
        self, user: User, oauth_account: Any, update_dict: dict
    ) -> User:
        raise NotImplementedError("OAuth not yet supported")


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[UserDatabase, None]:
    yield UserDatabase(session)


cookie_transport = CookieTransport(
    cookie_name="trackercg_session",
    cookie_max_age=settings.jwt_lifetime_seconds,
    cookie_secure=settings.cookie_secure,
    cookie_httponly=True,
    cookie_samesite="strict",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.jwt_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


class UserManager(IntegerIDMixin, BaseUserManager[User, USER_ID]):
    reset_password_token_lifetime_seconds = 3600
    verification_token_lifetime_seconds = 3600

    async def validate_password(
        self, password: str, user: User
    ) -> None:
        if len(password) < 8:
            raise InvalidPasswordException("Password must be at least 8 characters")
        if len(password) > 128:
            raise InvalidPasswordException("Password must be at most 128 characters")
        if not any(c.isupper() for c in password):
            raise InvalidPasswordException("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in password):
            raise InvalidPasswordException("Password must contain at least one digit")
        if password.lower() == user.email.lower():
            raise InvalidPasswordException("Password must not match the email address")


async def get_user_manager(
    user_db: UserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, USER_ID](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user(active=True)
