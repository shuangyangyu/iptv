#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
对外 :4022 的薄代理：APTV 探测用 HEAD，udpxy 只认 GET。
HEAD/OPTIONS 直接 200；其它请求流式转到 127.0.0.1:backend_port。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_HEAD_OK = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: video/mp2t\r\n"
    b"Cache-Control: no-store\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)


class UdpxyHeadProxy:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[asyncio.AbstractServer] = None
        self._ready = threading.Event()
        self._error = ""

    def start(
        self,
        listen_host: str,
        listen_port: int,
        backend_host: str,
        backend_port: int,
    ) -> tuple[bool, str]:
        self.stop()
        self._ready.clear()
        self._error = ""
        self._thread = threading.Thread(
            target=self._thread_main,
            args=(listen_host, listen_port, backend_host, backend_port),
            name="udpxy-head-proxy",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5):
            self.stop()
            return False, self._error or "HEAD 代理启动超时"
        if self._error:
            return False, self._error
        logger.info(
            "UDPXY HEAD 代理: %s:%s → %s:%s",
            listen_host,
            listen_port,
            backend_host,
            backend_port,
        )
        return True, f"HEAD 代理监听 {listen_host}:{listen_port}"

    def stop(self) -> None:
        loop = self._loop
        server = self._server
        if loop and server:
            try:
                loop.call_soon_threadsafe(server.close)
            except Exception:
                pass
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)
        self._thread = None
        self._loop = None
        self._server = None
        self._ready.clear()

    def _thread_main(
        self,
        listen_host: str,
        listen_port: int,
        backend_host: str,
        backend_port: int,
    ) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)

        async def _run() -> None:
            try:
                self._server = await asyncio.start_server(
                    lambda r, w: self._handle(r, w, backend_host, backend_port),
                    host=listen_host if listen_host not in ("0.0.0.0", "") else "0.0.0.0",
                    port=listen_port,
                    reuse_address=True,
                )
            except Exception as e:
                self._error = str(e)
                logger.error("UDPXY HEAD 代理监听失败: %s", e)
            finally:
                self._ready.set()
            if self._server:
                async with self._server:
                    await self._server.serve_forever()

        try:
            loop.run_until_complete(_run())
        except RuntimeError:
            # loop.stop() 会走到这里
            pass
        except Exception as e:
            self._error = str(e)
            logger.error("UDPXY HEAD 代理退出: %s", e)
            self._ready.set()
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        backend_host: str,
        backend_port: int,
    ) -> None:
        try:
            req = await _read_headers(reader)
            if not req:
                return
            first = req.split(b"\r\n", 1)[0].decode("latin-1", errors="ignore")
            method = (first.split(" ", 1)[0] or "").upper()
            if method in ("HEAD", "OPTIONS"):
                writer.write(_HEAD_OK)
                await writer.drain()
                return
            b_reader, b_writer = await asyncio.open_connection(backend_host, backend_port)
            try:
                b_writer.write(req)
                await b_writer.drain()
                await asyncio.gather(
                    _pipe(reader, b_writer),
                    _pipe(b_reader, writer),
                    return_exceptions=True,
                )
            finally:
                try:
                    b_writer.close()
                    await b_writer.wait_closed()
                except Exception:
                    pass
        except Exception as e:
            logger.debug("HEAD 代理连接结束: %s", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


async def _read_headers(reader: asyncio.StreamReader, limit: int = 65536) -> bytes:
    buf = b""
    deadline = time.monotonic() + 10
    while b"\r\n\r\n" not in buf:
        remain = deadline - time.monotonic()
        if remain <= 0:
            break
        chunk = await asyncio.wait_for(reader.read(4096), timeout=remain)
        if not chunk:
            break
        buf += chunk
        if len(buf) > limit:
            break
    return buf


async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await src.read(64 * 1024)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except Exception:
        pass
    try:
        dst.close()
    except Exception:
        pass


_proxy = UdpxyHeadProxy()


def start_head_proxy(
    listen_host: str,
    listen_port: int,
    backend_host: str,
    backend_port: int,
) -> tuple[bool, str]:
    return _proxy.start(listen_host, listen_port, backend_host, backend_port)


def stop_head_proxy() -> None:
    _proxy.stop()
