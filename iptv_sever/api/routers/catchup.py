#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回放代理 API 路由
"""

import urllib.error
import urllib.request
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..config import logger

# 导入回放地址转换模块
try:
    from iptv_sever.backend.catchup import (
        build_catchup_url,
        convert_catchup_times,
        detect_time_format,
    )
except ImportError as e:
    logger.error(f"导入回放模块失败: {e}")
    def detect_time_format(time_str: str):
        return None
    def build_catchup_url(*args, **kwargs):
        return ""
    def convert_catchup_times(begin: str, end: str):
        return (begin, end)

router = APIRouter(prefix="/api/v1", tags=["回放代理"])


@router.get("/catchup/{catchup_path:path}")
@router.post("/catchup/{catchup_path:path}")
async def catchup_proxy(
    catchup_path: str,
    request: Request,
    programbegin: str = Query(None, alias="programbegin"),
    programend: str = Query(None, alias="programend"),
    start: str = Query(None),
    end: str = Query(None),
):
    """
    回放代理服务
    
    接收播放器的回放请求，转换时间格式，转发到实际的回放接口
    """
    try:
        # 提取时间参数（支持两种格式：programbegin/programend 或 start/end）
        begin = programbegin or start
        end_time = programend or end
        
        if not begin or not end_time:
            raise HTTPException(
                status_code=400,
                detail="缺少时间参数 programbegin/programend 或 start/end"
            )
        
        # URL 解码
        begin = unquote(begin)
        end_time = unquote(end_time)
        
        logger.info(f"收到回放请求: {catchup_path}")
        logger.info(f"  原始 programbegin: {begin}")
        logger.info(f"  原始 programend: {end_time}")
        
        # 检查是否是占位符
        if begin == '{start}' or end_time == '{end}':
            raise HTTPException(
                status_code=400,
                detail="时间参数未替换，播放器可能不支持 catchup-source 模板格式"
            )
        
        # 检测并转换时间格式
        try:
            begin_format = detect_time_format(begin)
            end_format = detect_time_format(end_time)
            
            if begin_format is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"无法识别时间格式: programbegin={begin}"
                )
            
            if end_format is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"无法识别时间格式: programend={end_time}"
                )
            
            # 转换为 ZTE_EPG16 需要的格式
            begin_zte, end_zte = convert_catchup_times(begin, end_time)
            
            logger.info(f"  转换后 programbegin: {begin_zte}")
            logger.info(f"  转换后 programend: {end_zte}")
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"时间格式转换失败: {e}")
            raise HTTPException(status_code=400, detail=f"时间格式转换失败: {str(e)}")
        
        # 从配置中读取回放服务器地址
        from ..services.state import get_config
        
        cfg = get_config()
        catchup_config = cfg.get("catchup", {})
        
        target_host = catchup_config.get("target_host", "10.255.129.26")
        target_port = catchup_config.get("target_port", 6060)
        virtual_domain_config = catchup_config.get("virtual_domain", "hls.tvod_hls.zte.com")
        
        # 获取额外的查询参数
        query_params = dict(request.query_params)
        extra_params = {}
        for key, value in query_params.items():
            if key not in ('programbegin', 'programend', 'start', 'end'):
                extra_params[key] = value
        
        # 使用后端模块构建回放URL
        target_url = build_catchup_url(
            catchup_path=catchup_path,
            programbegin=begin,
            programend=end_time,
            target_host=target_host,
            target_port=target_port,
            virtual_domain=virtual_domain_config,
            extra_params=extra_params if extra_params else None,
        )
        
        logger.info(f"  转发到: {target_url}")
        
        # 转发请求
        try:
            req = urllib.request.Request(target_url)
            req.add_header('User-Agent', request.headers.get('user-agent', 'Mozilla/5.0'))
            
            class PreserveParamsRedirectHandler(urllib.request.HTTPRedirectHandler):
                def http_error_302(self, req, fp, code, msg, headers):
                    location = headers.get('Location', '')
                    if location:
                        logger.debug(f"  重定向到: {location}")
                    return super().http_error_302(req, fp, code, msg, headers)
            
            opener = urllib.request.build_opener(PreserveParamsRedirectHandler())
            opener.addheaders = [('User-Agent', request.headers.get('user-agent', 'Mozilla/5.0'))]
            
            with opener.open(req, timeout=30) as response:
                content = response.read()
                headers = dict(response.headers)
                
                return Response(
                    content=content,
                    status_code=response.status,
                    headers=headers,
                )
        
        except urllib.error.HTTPError as e:
            logger.error(f"转发请求失败 (HTTP {e.code}): {e.reason}")
            return Response(
                content=e.read() if hasattr(e, 'read') else b'',
                status_code=e.code,
                headers=dict(e.headers) if hasattr(e, 'headers') else {},
            )
        except Exception as e:
            logger.error(f"转发请求异常: {e}")
            raise HTTPException(status_code=500, detail=f"转发请求失败: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回放代理异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"回放代理异常: {str(e)}")

