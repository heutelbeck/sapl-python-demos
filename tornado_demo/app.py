"""SAPL Tornado Demo -- main application entry point."""

from __future__ import annotations

import os

import structlog
import tornado.ioloop
import tornado.web
from dotenv import load_dotenv

from sapl_tornado.config import SaplConfig
from sapl_tornado.dependencies import configure_sapl

from handlers import register_all_handlers
from routes.basic import BasicHandlers
from routes.constraints import ConstraintHandlers
from routes.services import ServiceHandlers
from routes.streaming import StreamingHandlers

log = structlog.get_logger()
load_dotenv()


class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write({"status": "ok", "application": "SAPL Tornado Demo"})


def make_app() -> tornado.web.Application:
    return tornado.web.Application(
        [(r"/", RootHandler)]
        + BasicHandlers
        + ConstraintHandlers
        + StreamingHandlers
        + ServiceHandlers
    )


def main() -> None:
    pdp_url = os.getenv("SAPL_PDP_URL", "http://localhost:8443")
    configure_sapl(SaplConfig(base_url=pdp_url, allow_insecure_connections=True))
    register_all_handlers()

    port = int(os.getenv("PORT", "3000"))
    app = make_app()
    app.listen(port)
    log.info("SAPL Tornado Demo listening", port=port, pdp=pdp_url)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
