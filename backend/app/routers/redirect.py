from typing import Annotated

from fastapi import APIRouter, Path, Request
from fastapi.responses import RedirectResponse

from .. import repository
from ..codes import referrer_host
from ..deps import DbConn
from ..errors import AppError
from ..schemas import CODE_PATTERN

router = APIRouter(tags=["redirect"])


@router.get("/r/{code}", response_class=RedirectResponse, status_code=302)
def follow_link(code: Annotated[str, Path(pattern=CODE_PATTERN)], request: Request, conn: DbConn):
    target = repository.find_target_and_record_click(conn, code, referrer_host(request.headers.get("referer")))
    if target is None:
        raise AppError(404, "not_found", "This short link doesn't exist or was deleted.")
    # 302, not 301: browsers cache 301s and would skip this server (and the click count) next time.
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": "no-store"})
