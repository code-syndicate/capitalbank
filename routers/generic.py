from fastapi import APIRouter, HTTPException, Query, Request, Response, Depends, BackgroundTasks
from typing import Union
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models.settings import Settings
from models.users import *
from lib.db import Collections, db
from lib.utils import hash_password
from lib.dependencies import get_session_user, propagate_info, get_msgs
from lib.emails.send_mail import dispatch_email

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
    out_transfers = await db[Collections.transfers].find({"sender": user.email}).sort("created", -1).to_list(length=100)
    # in_transfers = await db[Collections.transfers].find({"receiver": user.email}).sort("created", -1).to_list(length=100)

    txs = out_transfers[:10]

    return templates.TemplateResponse("dashboard.html", {"settings": settings, "request": request, "user": user, "tab": tab, "txs": txs})


@router.get("/sign-out", tags=["Sign out"], )
async def sign_out(auth:  UserDBModel = Depends(get_session_user)):
    if not auth:
        return RedirectResponse("/sign-in")

    _, log_out = auth

    await log_out()

    return RedirectResponse("/")


@router.get("/forgot-password", tags=["Forgot Password"], )
async def forgot_password(request:  Request, msg: str = Query(alias="msg", default="")):

    return templates.TemplateResponse("forgot-password.html", {"settings":  settings, "request":  request, "msg": msg})


@router.get("/reset-password", tags=["Confirm Forgot Password"], )
async def confirm_forget_password(t:  str = Query(alias="t", default="")):

    if not t:
        return RedirectResponse("/forgot-password?msg=Invalid reset token.")

    store = await db[Collections.password_reset_stores].find_one({"uid": t})

    if not store:
        return RedirectResponse("/forgot-password?msg=Invalid reset token.")

    await db[Collections.users].update_one({"email": store["email"]}, {"$set": {"password_hash": hash_password(store["password"])}})

    await db[Collections.password_reset_stores].delete_many({"email": store["email"]})

    return RedirectResponse("/sign-in?msg=Password reset successful. You can now sign in with your new password.")


@router.post("/forgot-password", tags=["Forgot Password - POST"], )
async def forgot_password(body:  PasswordResetInput, bg_task:  BackgroundTasks):

    u = await db[Collections.users].find_one({"email": body.email})

    if not u:
        raise HTTPException(401, "Invalid email address.")

    await db[Collections.password_reset_stores].delete_many({
        "email":  body.email
    })

    store = PasswordResetStore(
        email=body.email,
        password=body.password,
        password2=body.password2,
    )
    await db[Collections.password_reset_stores].insert_one(
        store.dict()
    )

    url = f"{settings.base_url}/reset-password?t={store.uid}"

    dispatch_email(bg_task, body.email, "password_reset", {
        "url": url
    })

    if settings.debug:
        print("RESET URL: ",  url)

    return


@router.get("/sign-in", tags=["Login"], response_class=HTMLResponse,)
async def signin(request:  Request, auth:  UserDBModel = Depends(get_session_user), msgs:  list[str] = Depends(get_msgs), msg: str = Query(alias="msg", default="")):
    # print(msgs)

    user, _ = auth if auth else (None, None)
    if user:
        return RedirectResponse("/apps/dashboard")

    return templates.TemplateResponse("signin.html", {"settings":  settings, "request":  request, "msgs":  msgs, "msg": msg})


@router.post("/sign-in", tags=["Login"], )
async def signin_post(form:  RequestAccessTokenInput, response:  Response, bg_task:  BackgroundTasks):

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

    dispatch_email(bg_task, user.email, "login", {})

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
async def change_user_password(form: ChangePasswordInput, bg_task:  BackgroundTasks, auth:  UserDBModel = Depends(get_session_user)):
    user, _ = auth

    guessed_password_hash = hash_password(form.old_password)

    if user.password_hash != guessed_password_hash:

        raise HTTPException(401, "The password you entered is incorrect.")

    if form.new_password != form.new_password2:

        raise HTTPException(401, "New passwords do not match.")

    otp_db = await db[Collections.otps].find_one({"user": user.email, "is_valid": True, "otp": form.otp})

    if not otp_db:
        raise HTTPException(401, "Invalid OTP")

    else:
        await db[Collections.otps].update_one({"user": user.email, "is_valid": True, "otp": form.otp}, {"$set":  {"is_valid": False}})

    new_password_hash = hash_password(form.new_password)

    await db[Collections.users].update_one({"uid": user.uid}, {"$set": {"password_hash": new_password_hash}})
    await db[Collections.sessions].delete_many({"user_id": user.uid})

    dispatch_email(bg_task, user.email, "password_change", {})


@router.post("/tx/in")
async def create_in_transaction(form: TransferInput1, bg_task: BackgroundTasks, auth:  UserDBModel = Depends(get_session_user),):
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

    dispatch_email(bg_task, user.email, "transfer", {
        "firstname": user.firstname,
        "amount": tx.amount,
        "description": form.description,
        "receiver": receiving_user["email"],
        "balance": user.balance,
        "type": "internal"
    })


@router.post("/tx/out")
async def create_out_transaction(form: TransferInput2, bg_task: BackgroundTasks, auth:  UserDBModel = Depends(get_session_user)):
    user, _ = auth

    if form.amount == 0:
        raise HTTPException(401, "Amount cannot be zero.")

    if form.amount > user.balance:
        raise HTTPException(401, "Insufficient balance.")

    tx = OutFiatTransfer(
        sender=user.email,
        amount=form.amount,
        txtype=TxType.DEBIT,
        description=form.description,
        receiver_account_name=form.receiver_account_name,
        receiver_account_number=form.receiver_account_number,
        receiver_bank_name=form.receiver_bank_name,
        scope=form.scope.upper(),
    )

    user.balance -= form.amount

    await db[Collections.transfers].insert_one(tx.dict())
    await db[Collections.users].update_one({"uid": user.uid}, {"$set": user.dict()})

    dispatch_email(bg_task, user.email, "transfer", {
        "firstname": user.firstname,
        "amount": tx.amount,
        "description": form.description,
        "receiver": tx.receiver_account_name,
        "balance": user.balance,
        "type": "external"

    })
