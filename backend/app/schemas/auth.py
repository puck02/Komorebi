from pydantic import BaseModel, EmailStr, Field


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: str
    email: EmailStr

    model_config = {"from_attributes": True}


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
