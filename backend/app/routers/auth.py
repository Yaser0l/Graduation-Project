from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.auth import UserCreate, UserOut, Token
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    check_query = text("SELECT id FROM users WHERE email = :email")
    result = await db.execute(check_query, {"email": user_in.email})
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    hashed_password = get_password_hash(user_in.password)
    insert_query = text(
        "INSERT INTO users (name, email, password_hash) VALUES (:name, :email, :password_hash) "
        "RETURNING id, name, email, created_at"
    )
    result = await db.execute(
        insert_query,
        {"name": user_in.name, "email": user_in.email, "password_hash": hashed_password},
    )
    user_data = result.first()
    await db.commit()

    user_out = UserOut(
        id=user_data.id,
        name=user_data.name,
        email=user_data.email,
        created_at=user_data.created_at,
    )
    token = create_access_token(subject=user_out.id)
    return {"access_token": token, "token_type": "bearer", "user": user_out}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    email = form_data.username  # OAuth2 uses 'username' field
    password = form_data.password

    query = text("SELECT * FROM users WHERE email = :email")
    result = await db.execute(query, {"email": email})
    user = result.first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_out = UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )
    token = create_access_token(subject=user_out.id)
    return {"access_token": token, "token_type": "bearer", "user": user_out}
