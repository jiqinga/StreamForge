import contextvars

CTX_USER_ID: contextvars.ContextVar[int] = contextvars.ContextVar("user_id", default=0)
CTX_X_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("x_request_id", default="")
