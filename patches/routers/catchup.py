#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回看代理 API

- 直播：udpxy（M3U 里 4022/rtp/...）
- 回看：/catchup/... 转运营商，并把 m3u8/.ts 改写成 /catchup/media 反代
  播放器只访问局域网，由服务器经 source_iface 拉 IPTV 内网（10.255）
"""

from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..config import logger

try:
    from iptv_sever.backend.catchup import (
        build_catchup_url,
        convert_catchup_times,
        detect_time_format,
    )
    from iptv_sever.backend.catchup_proxy import (
        decode_upstream_token,
        fetch_upstream,
        is_allowed_upstream_url,
        looks_like_m3u8,
        looks_like_ts,
        rewrite_m3u8_to_proxy,
    )
except ImportError as e:
    logger.error(f"导入回放模块失败: {e}")

    def detect_time_format(time_str: str):
        return None

    def build_catchup_url(*args, **kwargs):
        return ""

    def convert_catchup_times(begin: str, end: str):
        return (begin, end)

    def decode_upstream_token(u: str):
        return u

    def is_allowed_upstream_url(url: str):
        return False

    def looks_like_m3u8(content_type: str, content: bytes):
        return False

    def looks_like_ts(url: str, content_type: str):
        return False

    def rewrite_m3u8_to_proxy(*args, **kwargs):
        return b""

    def fetch_upstream(*args, **kwargs):
        raise RuntimeError("catchup proxy unavailable")


router = APIRouter(prefix="/api/v1", tags=["回放代理"])

_DROP_HEADERS = {
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade",
    "content-encoding",
    "content-length",
    "server",
    "date",
}


def _public_base(request: Request) -> str:
    """播放器访问的局域网地址（8088）。"""
    from ..services.state import get_config, get_server_base_url

    cfg_base = get_server_base_url(get_config(), port=8088).rstrip("/")
    if cfg_base:
        return cfg_base

    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        if host.endswith(":8089"):
            host = host[:-5] + ":8088"
        elif ":" not in host:
            host = f"{host}:8088"
        return f"{proto}://{host}"
    return "http://127.0.0.1:8088"


def _media_proxy_base(request: Request) -> str:
    return f"{_public_base(request)}/catchup/media"


def _filter_headers(headers: dict) -> dict:
    out = {}
    for k, v in (headers or {}).items():
        if k.lower() in _DROP_HEADERS:
            continue
        out[k] = v
    return out


def _proxy_and_rewrite(
    upstream_url: str,
    *,
    request: Request,
    source_iface: str,
    timeout: float = 60,
) -> Response:
    ua = request.headers.get("user-agent", "Mozilla/5.0")
    status, headers, body, final_url = fetch_upstream(
        upstream_url,
        source_iface=source_iface,
        user_agent=ua,
        timeout=timeout,
        on_redirect=lambda u: logger.debug(f"  重定向到: {u}"),
    )
    ctype = headers.get("Content-Type") or headers.get("content-type") or ""
    headers = dict(headers)

    if looks_like_m3u8(ctype, body):
        proxy_base = _media_proxy_base(request)
        body = rewrite_m3u8_to_proxy(
            body,
            playlist_url=final_url or upstream_url,
            proxy_base=proxy_base,
        )
        headers["Content-Type"] = "application/vnd.apple.mpegurl"
        logger.info(f"  已重写 m3u8 → 经 {proxy_base}")
    elif looks_like_ts(final_url or upstream_url, ctype):
        headers["Content-Type"] = "video/mp2t"

    return Response(
        content=body,
        status_code=status,
        headers=_filter_headers(headers),
        media_type=headers.get("Content-Type") or headers.get("content-type"),
    )


@router.get("/catchup/media")
@router.post("/catchup/media")
async def catchup_media_proxy(
    request: Request,
    u: str = Query(..., description="上游媒体 URL（base64url）"),
):
    """反代 CDN 子 m3u8 / .ts，强制经 source_iface。"""
    upstream = decode_upstream_token(u)
    if not upstream:
        raise HTTPException(status_code=400, detail="缺少参数 u")
    if not is_allowed_upstream_url(upstream):
        raise HTTPException(status_code=400, detail="不允许代理该地址")

    from ..services.state import get_config

    cfg = get_config()
    source_iface = cfg.get("source_iface") or ""
    logger.info(f"媒体反代: iface={source_iface or '-'} url={upstream[:160]}")

    try:
        return _proxy_and_rewrite(
            upstream,
            request=request,
            source_iface=source_iface,
            timeout=60,
        )
    except Exception as e:
        logger.error(f"媒体反代失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"媒体反代失败: {e}")


@router.get("/catchup/{catchup_path:path}")
@router.post("/catchup/{catchup_path:path}")
async def catchup_proxy(
    catchup_path: str,
    request: Request,
    programbegin: str = Query(None, alias="programbegin"),
    programend: str = Query(None, alias="programend"),
    start: str = Query(None),
    end: str = Query(None),
    utc: str = Query(None),
    lutc: str = Query(None),
    duration: str = Query(None),
):
    """
    回看入口：时间转换 → 运营商 → 重写 m3u8 为本地反代地址
    """
    try:
        if catchup_path == "media":
            raise HTTPException(status_code=400, detail="请使用 /catchup/media?u=...")

        begin = programbegin or start or utc
        end_time = programend or end
        duration_raw = duration

        if not end_time and lutc:
            lutc_s = unquote(str(lutc)).strip()
            if lutc_s.isdigit():
                lutc_n = int(lutc_s)
                if lutc_n >= 1_000_000_000:
                    end_time = lutc_s
                else:
                    duration_raw = lutc_s
            else:
                end_time = lutc_s

        if begin and not end_time and duration_raw:
            begin_s = unquote(str(begin)).strip()
            dur_s = unquote(str(duration_raw)).strip()
            if begin_s.isdigit() and dur_s.isdigit():
                end_time = str(int(begin_s) + int(dur_s))

        if not begin or not end_time:
            raise HTTPException(
                status_code=400,
                detail="缺少时间参数 programbegin/programend 或 start/end",
            )

        begin = unquote(begin)
        end_time = unquote(end_time)

        logger.info(f"收到回放请求: {catchup_path}")
        logger.info(f"  原始 programbegin: {begin}")
        logger.info(f"  原始 programend: {end_time}")

        if begin in ("{start}", "{utc}") or end_time in (
            "{end}",
            "{utcend}",
            "{lutc}",
        ):
            raise HTTPException(
                status_code=400,
                detail="时间参数未替换，播放器可能不支持 catchup-source 模板格式",
            )

        try:
            if detect_time_format(begin) is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"无法识别时间格式: programbegin={begin}",
                )
            if detect_time_format(end_time) is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"无法识别时间格式: programend={end_time}",
                )
            begin_zte, end_zte = convert_catchup_times(begin, end_time)
            logger.info(f"  转换后 programbegin: {begin_zte}")
            logger.info(f"  转换后 programend: {end_zte}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"时间格式转换失败: {e}")
            raise HTTPException(status_code=400, detail=f"时间格式转换失败: {str(e)}")

        from ..services.state import get_config

        cfg = get_config()
        catchup_config = cfg.get("catchup", {}) or {}
        source_iface = cfg.get("source_iface") or ""

        target_host = catchup_config.get("target_host", "10.255.129.26")
        target_port = catchup_config.get("target_port", 6060)
        virtual_domain_config = catchup_config.get(
            "virtual_domain", "hls.tvod_hls.zte.com"
        )

        query_params = dict(request.query_params)
        extra_params = {}
        skip = {
            "programbegin",
            "programend",
            "start",
            "end",
            "utc",
            "lutc",
            "duration",
        }
        for key, value in query_params.items():
            if key not in skip:
                extra_params[key] = value

        target_url = build_catchup_url(
            catchup_path=catchup_path,
            programbegin=begin,
            programend=end_time,
            target_host=target_host,
            target_port=target_port,
            virtual_domain=virtual_domain_config,
            extra_params=extra_params if extra_params else None,
        )

        logger.info(
            f"  转发到: {target_url} (source_iface={source_iface or '-'})"
        )

        try:
            return _proxy_and_rewrite(
                target_url,
                request=request,
                source_iface=source_iface,
                timeout=30,
            )
        except Exception as e:
            logger.error(f"转发请求异常: {e}")
            raise HTTPException(status_code=500, detail=f"转发请求失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回放代理异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"回放代理异常: {str(e)}")
