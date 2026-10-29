from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, UploadFile


class _Created:
    def __init__(self, request: Request, response: Response):
        self._base = request.url.path.rstrip("/")
        self._response = response

    def __call__(self, resource_id) -> None:
        self._response.headers["Location"] = f"{self._base}/{resource_id}"


SetLocation = Annotated[_Created, Depends()]


async def read_upload(file: UploadFile, *extensions: str) -> bytes:
    if not file.filename or not file.filename.lower().endswith(extensions):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(extensions)}")
    return await file.read()


def reject_rows_outside_program(rows: list[int]) -> None:
    if rows:
        raise HTTPException(
            status_code=403,
            detail={"message": "Rows outside your program. Nothing was imported.", "rows": rows},
        )
