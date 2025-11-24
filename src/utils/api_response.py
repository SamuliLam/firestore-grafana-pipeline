from starlette.responses import JSONResponse


def make_response(status: str, message: str, data=None, status_code=200):
    content = {"status": status, "message": message}
    if data is not None:
        content["data"] = data
    return JSONResponse(status_code=status_code, content=content)
