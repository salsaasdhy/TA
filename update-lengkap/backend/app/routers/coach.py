import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import analysis, rag
from ..config import settings
from ..database import get_db
from ..bank_soal import Soal, load_soal
from ..models import ActionItem, ChatMessage, Submission, User
from ..schemas import (ActionOut, ChatIn, ChatMessageOut, DashboardOut, HistoryItem,
                       OptionOut, QuestionOut, SubmitIn)
from ..security import current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["coach"])


def _latest(db: Session, user: User) -> Submission | None:
    return db.scalars(select(Submission).where(Submission.user_id == user.id)
                      .order_by(Submission.id.desc()).limit(1)).first()


def _dashboard(user: User, sub: Submission | None) -> DashboardOut:
    first = user.name.split()[0]
    if not sub:
        return DashboardOut(has_data=False, first_name=first)
    return DashboardOut(
        has_data=True, first_name=first, submitted_at=sub.created_at, style=sub.style,
        consistency=sub.consistency, issue_count=sub.issue_count, insights=sub.insights,
        actions=[ActionOut.model_validate(a) for a in sub.actions])


def _q_out(q: Soal) -> QuestionOut:
    cfg = {k: v for k, v in (q.config or {}).items() if k != "rules"}  # aturan skor tidak dikirim ke klien
    return QuestionOut(id=q.id, order=q.order, category=q.category, text=q.text, qtype=q.qtype,
                       required=q.required, config=cfg,
                       options=[OptionOut(id=o["id"], text=o["text"]) for o in q.options])


@router.get("/questions", response_model=list[QuestionOut])
def questions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_q_out(q) for q in load_soal(db, user.semester)]


@router.post("/questionnaire/submit", response_model=DashboardOut, status_code=201)
def submit(body: SubmitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    qs = load_soal(db, user.semester)
    try:
        result = analysis.analyze(qs, body.answers, profil={"semester": user.semester, "prodi": user.program_studi})
    except ValueError as e:
        raise HTTPException(422, str(e))
    cards, actions = analysis.build_insights(result)
    sub = Submission(user_id=user.id, answers={str(k): v for k, v in body.answers.items()},
                     style=result["style"], consistency=result["consistency"],
                     issue_count=result["issue_count"], flags=result["flags"], insights=cards,
                     summary=result["summary"], facts=result["facts"])
    sub.actions = [ActionItem(user_id=user.id, text=t) for t in actions]
    db.add(sub)
    db.commit()
    return _dashboard(user, sub)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _dashboard(user, _latest(db, user))


@router.patch("/actions/{action_id}", response_model=ActionOut)
def toggle_action(action_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(ActionItem, action_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Rencana aksi tidak ditemukan.")
    item.done = not item.done
    db.commit()
    return item


@router.get("/history", response_model=list[HistoryItem])
def history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Submission).where(Submission.user_id == user.id)
                      .order_by(Submission.id.desc())).all()
    return [HistoryItem(id=r.id, created_at=r.created_at, style=r.style,
                        consistency=r.consistency, issue_count=r.issue_count) for r in rows]


@router.get("/chat", response_model=list[ChatMessageOut])
def chat_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id)
                      .order_by(ChatMessage.id).limit(200)).all()


@router.post("/chat", response_model=ChatMessageOut)
def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not settings.openrouter_api_key:
        raise HTTPException(503, "OPENROUTER_API_KEY belum diatur di backend/.env.")
    prev = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id)
                      .order_by(ChatMessage.id.desc()).limit(8)).all()
    history = [(m.role, m.content) for m in reversed(prev)]
    sub = _latest(db, user)
    summary = ((sub.summary or f"gaya belajar {sub.style}, konsistensi {sub.consistency}%")
               if sub else "belum mengisi kuisioner")
    try:
        text, source = rag.answer(body.message, history, summary)
    except Exception:
        log.exception("Chat gagal")
        raise HTTPException(502, "AI Coach sedang tidak bisa dihubungi. Coba lagi sebentar.")
    db.add(ChatMessage(user_id=user.id, role="user", content=body.message))
    reply = ChatMessage(user_id=user.id, role="assistant", content=text, source=source)
    db.add(reply)
    db.commit()
    return reply
