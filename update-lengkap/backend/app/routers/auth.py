from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Submission, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut, UserUpdate
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(db: Session, user: User) -> UserOut:
    count = db.scalar(select(func.count(Submission.id)).where(Submission.user_id == user.id)) or 0
    out = UserOut.model_validate(user)
    out.submission_count = count
    return out


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(409, "Email sudah terdaftar.")
    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password),
                nim=body.nim, program_studi=body.program_studi, angkatan=body.angkatan,
                semester=body.semester)
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email atau kata sandi salah.")
    return TokenOut(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(db, user)


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    return user_out(db, user)
