"""
聊天资源模块

统一处理所有聊天相关的操作
"""

import logging

from flask import request
from flask_restful import Resource

from services.chat_service import ChatService
from utils.request_manager.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ChatResource(Resource):
    """聊天资源类 - 统一处理所有聊天操作"""

    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service

    def get(self, session_id=None):
        """获取会话列表或单个会话信息（包含消息）"""
        try:
            if session_id:
                # 获取指定会话的信息和消息
                session = self.chat_service.get_session(session_id)
                if not session:
                    return {"success": False, "message": "会话不存在"}, 404

                # 获取会话的所有消息
                messages = self.chat_service.get_session_messages(session_id)

                # 返回会话信息和消息的完整数据
                result = {
                    "id": session["id"],
                    "title": session["title"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "messages": messages,
                }

                return {"success": True, "data": result}
            else:
                # 获取所有会话
                sessions = self.chat_service.get_all_sessions()
                return {"success": True, "data": {"sessions": sessions}}
        except Exception as e:
            logger.error(f"获取数据失败: {str(e)}")
            return {"success": False, "message": "获取数据失败"}, 500

    def post(self, session_id=None):
        """创建会话或发送消息"""
        try:
            if session_id:
                # 发送消息到指定会话（非流式）
                try:
                    data = request.get_json()
                except Exception as json_error:
                    logger.error(f"JSON解析失败: {str(json_error)}")
                    logger.error(f"请求内容: {request.get_data()}")
                    logger.error(f"Content-Type: {request.headers.get('Content-Type')}")
                    return {
                        "success": False,
                        "message": "请求格式错误，请检查JSON格式",
                    }, 400

                if not data:
                    return {"success": False, "message": "消息内容不能为空"}, 400

                query = (data.get("query") or data.get("content") or "").strip()
                if not query:
                    return {"success": False, "message": "query 不能为空"}, 400

                mode = (
                    (data.get("mode") or "normal").strip()
                    if isinstance(data, dict)
                    else "normal"
                )
                file_id = data.get("file_id") if isinstance(data, dict) else None
                kb_id = data.get("kb_id") if isinstance(data, dict) else None
                result = self.chat_service.send_message(
                    session_id,
                    query,
                    mode=mode,
                    file_id=file_id,
                    kb_id=kb_id,
                )
                return {"success": True, "data": result}
            else:
                # 创建新会话
                try:
                    data = request.get_json() or {}
                except Exception as json_error:
                    logger.error(f"JSON解析失败: {str(json_error)}")
                    logger.error(f"请求内容: {request.get_data()}")
                    logger.error(f"Content-Type: {request.headers.get('Content-Type')}")
                    return {
                        "success": False,
                        "message": "请求格式错误，请检查JSON格式",
                    }, 400

                title = data.get("title", "")

                session_id = self.chat_service.create_session(title)
                session = self.chat_service.get_session(session_id)

                return {"success": True, "data": session}, 201
        except ValidationError as e:
            logger.error(f"参数错误: {str(e)}")
            return {"success": False, "message": str(e)}, 400
        except NotFoundError as e:
            logger.error(f"资源不存在: {str(e)}")
            return {"success": False, "message": str(e)}, 404
        except ConfigurationError as e:
            logger.error(f"配置错误: {str(e)}")
            return {"success": False, "message": str(e)}, 500
        except ExternalServiceError as e:
            logger.error(f"外部服务错误: {str(e)}")
            return {"success": False, "message": str(e)}, 502
        except Exception as e:
            logger.error(f"操作失败: {str(e)}")
            return {"success": False, "message": "操作失败"}, 500

    def put(self, session_id):
        """更新会话标题"""
        try:
            if not session_id:
                return {"success": False, "message": "会话ID不能为空"}, 400

            try:
                data = request.get_json()
            except Exception as json_error:
                logger.error(f"JSON解析失败: {str(json_error)}")
                logger.error(f"请求内容: {request.get_data()}")
                logger.error(f"Content-Type: {request.headers.get('Content-Type')}")
                return {
                    "success": False,
                    "message": "请求格式错误，请检查JSON格式",
                }, 400

            if not data or "title" not in data:
                return {"success": False, "message": "标题不能为空"}, 400

            title = data["title"]
            self.chat_service.update_session_title(session_id, title)

            session = self.chat_service.get_session(session_id)
            return {"success": True, "data": session}
        except Exception as e:
            logger.error(f"更新会话失败: {str(e)}")
            return {"success": False, "message": "更新会话失败"}, 500

    def delete(self, session_id):
        """删除会话"""
        try:
            if not session_id:
                return {"success": False, "message": "会话ID不能为空"}, 400

            self.chat_service.delete_session(session_id)
            return {"success": True, "message": "会话删除成功"}
        except Exception as e:
            logger.error(f"删除会话失败: {str(e)}")
            return {"success": False, "message": "删除会话失败"}, 500
