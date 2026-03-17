# resources/knowledge_base_resource.py
from flask import request
from flask_restful import Resource

from services.knowledge_base_service import KnowledgeBaseService
from utils.request_manager.response import ApiResponse

import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseResource(Resource):
    """
    知识库资源
    """

    def __init__(self):
        self.kb_service = KnowledgeBaseService()

    def get(self, kb_id: str = None):
        """
        GET /knowledge-bases：返回全部知识库ID列表
        GET /knowledge-bases/<kb_id>：返回完整记录，支持多个ID如1,2,3
        GET /knowledge-bases/<kb_id>?attribute=field: 返回单字段或多字段（逗号分隔）
        """
        try:
            if kb_id is None:
                kbs, _ = self.kb_service.search_knowledge_bases()
                return ApiResponse.success("获取知识库ID列表成功", {"ids": [kb.id for kb in kbs]})

            # 支持多个ID，逗号分隔
            id_strs = kb_id.split(',')
            ids = []
            for id_str in id_strs:
                try:
                    ids.append(int(id_str.strip()))
                except ValueError:
                    return ApiResponse.bad_request(f"无效的ID: {id_str}")

            # 获取attribute参数
            attr_param = request.args.get("attribute", "")
            attrs = [a.strip() for a in attr_param.split(",") if a.strip()] if attr_param else []

            results = []
            for kb_id in ids:
                kb = self.kb_service.get_by_id(kb_id)
                if not kb:
                    return ApiResponse.not_found(f"知识库不存在: {kb_id}")

                data = kb.to_dict()

                if attrs:
                    invalid = [a for a in attrs if a not in data]
                    if invalid:
                        return ApiResponse.bad_request(f"无效字段: {', '.join(invalid)}")
                    results.append({a: data.get(a) for a in attrs})
                else:
                    results.append(data)

            if len(results) == 1:
                return ApiResponse.success("获取知识库成功", results[0])
            else:
                return ApiResponse.success("获取知识库成功", {"items": results})
        except Exception as e:
            logger.exception("获取知识库失败")
            return ApiResponse.internal_error("获取知识库失败", {"error": str(e)})

    def post(self, kb_id: int = None):
        """
        POST /knowledge-bases：创建知识库（仅 name 必填，嵌入模型固定为默认值）
        """
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        if not name:
            return ApiResponse.bad_request("缺少必填字段：name")

        try:
            kb = self.kb_service.create_knowledge_base(
                name=name,
                description=data.get("description"),
            )
            return ApiResponse.created("知识库创建成功", kb.to_dict())
        except Exception as e:
            logger.exception("创建知识库失败")
            return ApiResponse.internal_error("创建知识库失败", {"error": str(e)})

    def put(self, kb_id: str = None):
        """
        PUT /knowledge-bases/<kb_id>?attribute=field,field2 ：按ID更新字段（支持多字段）
        - 若 attribute 提供多个字段，Body 必须为 JSON 对象
        - 若未提供 attribute，Body 为 JSON 对象则按字段更新
        """
        if kb_id is None:
            return ApiResponse.bad_request("缺少知识库ID，无法更新")

        # 只支持单个ID更新
        try:
            kid = int(kb_id)
        except ValueError:
            return ApiResponse.bad_request("知识库ID 格式错误")

        attr_param = (request.args.get("attribute") or request.args.get("attr") or "").strip()
        attrs = [a.strip() for a in attr_param.split(",") if a.strip()] if attr_param else []

        value = request.get_json(silent=True)
        if value is None:
            return ApiResponse.bad_request("缺少更新内容（JSON）")

        try:
            kb = self.kb_service.get_by_id(kid)
            if not kb:
                return ApiResponse.not_found("知识库不存在")

            if attrs:
                if not isinstance(value, dict):
                    return ApiResponse.bad_request("多字段更新需提供 JSON 对象")
                invalid = [a for a in attrs if not hasattr(kb, a)]
                if invalid:
                    return ApiResponse.bad_request("无效字段")
                for a in attrs:
                    if a in value:
                        setattr(kb, a, value.get(a))
            else:
                if not isinstance(value, dict):
                    return ApiResponse.bad_request("缺少更新字段 attribute")
                invalid = [a for a in value.keys() if not hasattr(kb, a)]
                if invalid:
                    return ApiResponse.bad_request("无效字段")
                for a, v in value.items():
                    setattr(kb, a, v)

            updated = self.kb_service.update(kid, kb)
            return ApiResponse.success("知识库更新成功", updated.to_dict())
        except Exception as e:
            logger.exception("更新知识库失败")
            return ApiResponse.internal_error("更新知识库失败", {"error": str(e)})

    def delete(self, kb_id: str = None):
        """
        DELETE /knowledge-bases/<kb_id>：删除知识库（支持多个ID如1,2,3）
        """
        if kb_id is None:
            return ApiResponse.bad_request("缺少知识库ID")

        id_strs = kb_id.split(',')
        ids = []
        for id_str in id_strs:
            try:
                ids.append(int(id_str.strip()))
            except ValueError:
                return ApiResponse.bad_request(f"知识库ID 格式错误: {id_str}")

        deleted = []
        failed = []
        try:
            for kid in ids:
                try:
                    result = self.kb_service.delete_knowledge_base(kid)
                    if result:
                        deleted.append(kid)
                    else:
                        failed.append(kid)
                except Exception:
                    failed.append(kid)

            return ApiResponse.success("知识库删除完成", {"deleted": deleted, "failed": failed})
        except Exception as e:
            logger.exception("删除知识库失败")
            return ApiResponse.internal_error("删除知识库失败", {"error": str(e)})


class KnowledgeBaseRetrieveResource(Resource):
    """知识库检索（余弦相似度）"""

    def __init__(self):
        self.kb_service = KnowledgeBaseService()

    def post(self, kb_id: int):
        try:
            payload = request.get_json(silent=True) or {}
            query = payload.get("query")
            top_k = payload.get("top_k", 5)
            threshold = payload.get("threshold")

            result = self.kb_service.retrieve_by_cosine(kb_id=int(kb_id), query=query, top_k=top_k, threshold=threshold)
            return ApiResponse.success("检索成功", result)
        except Exception as e:
            logger.exception("检索失败")
            return ApiResponse.internal_error("检索失败", {"error": str(e)})


# 已移除知识库统计接口，改由前端多次 GET 汇总

