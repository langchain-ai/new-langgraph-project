from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def authenticate_user():
    return {"identity": "user-1", "foo": "bar", "is_authenticated": True}


@auth.on
async def on_authenticate_user(ctx: Auth.types.AuthContext, value: dict):
    if ctx.user.identity!= "langgraph-studio-user":
        assert ctx.user.foo == "bar"
