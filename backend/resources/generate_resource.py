import logging
import json
from flask import Response, request
from flask_restful import Resource

from llm.API.generating import generating

logger = logging.getLogger(__name__)


class GenerateResource(Resource):
    """统一文本生成（流式）。用于 RAG 管线的抽取与重写阶段。
    POST /api/v1/generate
    请求体：{ prompt: str }
    响应：text/plain 流，逐行："data: {json}\n\n"，最后 "data: [DONE]\n\n"
    """

    def post(self):
        try:
            payload = request.get_json(silent=True) or {}
            prompt = payload.get("prompt")
            if not prompt or not str(prompt).strip():
                return {"success": False, "message": "prompt 不能为空"}, 400

            def stream():
                try:
                    for chunk in generating(prompt):
                        payload_str = json.dumps({"content": chunk}, ensure_ascii=False)
                        yield f"data: {payload_str}\n\n"
                except Exception as e:
                    logger.error(f"生成失败: {e}")
                    err = json.dumps({"error": f"生成失败: {str(e)}"}, ensure_ascii=False)
                    yield f"data: {err}\n\n"
                finally:
                    yield "data: [DONE]\n\n"

            return Response(
                stream(),
                mimetype="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )
        except Exception as e:
            logger.error(f"生成接口异常: {e}")
            return {"success": False, "message": "生成接口异常"}, 500
