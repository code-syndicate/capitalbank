from fastapi import APIRouter, HTTPException, Query, Request, Response, Depends
from typing import Union
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models.settings import Settings
from models.users import AuthSession, ChangePasswordInput, RequestAccessTokenInput, TransferInput1, TxType, UserBaseModel, UserInputModel, UserDBModel, InFiatTransfer, OutFiatTransfer, TransferInput2
from lib.db import Collections, db
from lib.utils import hash_password
from lib.dependencies import get_session_user, propagate_info, get_msgs

settings = Settings()

templates = Jinja2Templates(directory="templates",  autoescape=True,)

router = APIRouter(
    tags=["Generic endpoints"]
)


@router.get("/", tags=["Home"], response_class=HTMLResponse)
async def index(request: Request):

    return RedirectResponse("/sign-in")

    # return templates.TemplateResponse("index.html", {"settings": settings, "request": request})


@router.get("/apps/dashboard", tags=["Dashboard"], response_class=HTMLResponse)
async def dashboard(request: Request, auth:  UserDBModel = Depends(get_session_user), tab: Union[str, None] = Query(alias="tab", default="dash"), msgs:  list[str] = Depends(get_msgs)):
    print(msgs)

    if not auth:
        return RedirectResponse("/sign-in")

    user,  _ = auth

    views = ["dash", "account", "transfers",
             "transactions", "profile", "settings"]

    if not tab.lower() in views:
        tab = views[0]

    # get all transfers
    out_transfers = await db[Collections.transfers].find({"sender": user.email}).to_list(length=100)
    in_transfers = await db[Collections.transfers].find({"receiver": user.email}).to_list(length=100)

    txs = out_transfers + in_transfers

    return templates.TemplateResponse("dashboard.html", {"settings": settings, "request": request, "user": user, "tab": tab, "txs": txs})


@router.get("/sign-out", tags=["Sign out"], )
async def sign_out(auth:  UserDBModel = Depends(get_session_user)):
    if not auth:
        return RedirectResponse("/sign-in")

    _, log_out = auth

    await log_out()

    return RedirectResponse("/")


@router.get("/sign-in", tags=["Login"], response_class=HTMLResponse,)
async def signin(request:  Request, auth:  UserDBModel = Depends(get_session_user), msgs:  list[str] = Depends(get_msgs)):
    print(msgs)

    user, _ = auth if auth else (None, None)
    if user:
        return RedirectResponse("/apps/dashboard")

    return templates.TemplateResponse("signin.html", {"settings":  settings, "request":  request, "msgs":  msgs})


@router.post("/sign-in", tags=["Login"], )
async def signin_post(form:  RequestAccessTokenInput, response:  Response):

    existing_user_with_email = await db[Collections.users].find_one({"email": form.email})

    if not existing_user_with_email:
        raise HTTPException(404, "No matching account.")

    user = UserDBModel(**existing_user_with_email)
    guessed_password_hash = hash_password(form.password)

    if user.password_hash != guessed_password_hash:

        raise HTTPException(401, "Invalid account credentials.")

    new_session = AuthSession(
        user_id=user.uid, duration_in_hours=48
    )

    await db[Collections.sessions].insert_one(new_session.dict())

    response.set_cookie(settings.session_cookie_name, new_session.uid)

    return


@router.post("/update-data")
async def update_user_data(form: UserBaseModel, auth:  UserDBModel = Depends(get_session_user)):
    data = form.dict()
    print(data)
    user, _ = auth

    user_dict = user.dict()

    user_dict.update(data)

    updated_user = UserDBModel(**user_dict)

    await db[Collections.users].update_one({"uid": user.uid}, {"$set": updated_user.dict()})


@router.post("/change-password")
async def change_user_password(form: ChangePasswordInput, auth:  UserDBModel = Depends(get_session_user)):
    user, _ = auth

    guessed_password_hash = hash_password(form.old_password)

    if user.password_hash != guessed_password_hash:

        raise HTTPException(401, "The password you entered is incorrect.")

    if form.new_password != form.new_password2:

        raise HTTPException(401, "New passwords do not match.")

    new_password_hash = hash_password(form.new_password)

    await db[Collections.users].update_one({"uid": user.uid}, {"$set": {"password_hash": new_password_hash}})
    await db[Collections.sessions].delete_many({"user_id": user.uid})


@router.post("/tx/in")
async def create_in_transaction(form: TransferInput1, auth:  UserDBModel = Depends(get_session_user)):
    user, _ = auth

    receiving_user = await db[Collections.users].find_one({"email": form.receiver})

    if not receiving_user:
        raise HTTPException(404, "No matching receiver account.")

    if user.uid == receiving_user["uid"]:
        raise HTTPException(401, "You cannot transfer to yourself.")

    if form.amount == 0:
        raise HTTPException(401, "Amount cannot be zero.")

    if form.amount > user.balance:
        raise HTTPException(401, "Insufficient balance.")

    otp_db = await db[Collections.otps].find_one({"user": user.email, "is_valid": True, "otp": form.otp})

    if not otp_db:
        raise HTTPException(401, "Invalid OTP")

    else:
        await db[Collections.otps].update_one({"user": user.email, "is_valid": True, "otp": form.otp}, {"$set":  {"is_valid": False}})

    tx = InFiatTransfer(
        sender=user.email,
        amount=form.amount,
        txtype=TxType.DEBIT,
        description=form.description,
        receiver=receiving_user["email"]
    )

    user.balance -= form.amount

    await db[Collections.transfers].insert_one(tx.dict())
    await db[Collections.users].update_one({"uid": user.uid}, {"$set": user.dict()})


@router.post("/tx/out")
async def create_out_transaction(form: TransferInput2, auth:  UserDBModel = Depends(get_session_user)):
    user, _ = auth

    if form.amount == 0:
        raise HTTPException(401, "Amount cannot be zero.")

    if form.amount > user.balance:
        raise HTTPException(401, "Insufficient balance.")

    otp_db = await db[Collections.otps].find_one({"user": user.email, "is_valid": True, "otp": form.otp})

    if not otp_db:
        raise HTTPException(401, "Invalid OTP")

    else:
        await db[Collections.otps].update_one({"user": user.email, "is_valid": True, "otp": form.otp}, {"$set":  {"is_valid": False}})

    tx = OutFiatTransfer(
        sender=user.email,
        amount=form.amount,
        txtype=TxType.DEBIT,
        description=form.description,
        receiver_account_name=form.receiver_account_name,
        receiver_account_number=form.receiver_account_number,
        receiver_bank_name=form.receiver_bank_name,
    )

    user.balance -= form.amount

    await db[Collections.transfers].insert_one(tx.dict())
    await db[Collections.users].update_one({"uid": user.uid}, {"$set": user.dict()})
