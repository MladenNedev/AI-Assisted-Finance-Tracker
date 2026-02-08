class AuthService:
    async def authenticate(self, email: str, password: str) -> None:
        raise NotImplementedError

    async def issue_session(self, user_id: str) -> None:
        raise NotImplementedError
