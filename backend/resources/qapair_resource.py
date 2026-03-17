import logging
from flask import request
from flask_restful import Resource

from services.qapair_service import QApairService
from utils.request_manager.response import ApiResponse
from utils.request_manager.exceptions import FileProcessingError

logger = logging.getLogger(__name__)


class QApairResource(Resource):
    """QApair 管理资源：POST 导入JSON文件到DB；GET 返回全量；DELETE 按ID删除"""

    def __init__(self):
        self.service = QApairService()

    @staticmethod
    def _to_dict(item):
        if item is None:
            return None
        if hasattr(item, "to_dict"):
            return item.to_dict()
        if isinstance(item, dict):
            return item
        return dict(item)

    def get(self, qa_id: str = None):
        """获取QApair，支持多个ID如1,2,3；?attribute=field返回字段（支持多字段，逗号分隔）"""
        try:
            if qa_id:
                # 支持多个ID，逗号分隔
                id_strs = qa_id.split(',')
                ids = []
                for id_str in id_strs:
                    try:
                        ids.append(int(id_str.strip()))
                    except ValueError:
                        return ApiResponse.bad_request(f"无效的QApair ID: {id_str}")

                # 获取attribute参数
                attr_param = request.args.get("attribute", "")
                attrs = [a.strip() for a in attr_param.split(",") if a.strip()] if attr_param else []

                results = []
                for qid in ids:
                    item = self.service.get_pair_by_id(qid)
                    if not item:
                        return ApiResponse.not_found(f"QApair 不存在: {qid}")

                    data = self._to_dict(item)

                    if attrs:
                        invalid = [a for a in attrs if a not in data]
                        if invalid:
                            return ApiResponse.bad_request(f"无效字段: {', '.join(invalid)}")
                        results.append({a: data.get(a) for a in attrs})
                    else:
                        results.append(data)

                if len(results) == 1:
                    return ApiResponse.success("获取 QApair 成功", {"item": results[0]})
                else:
                    return ApiResponse.success("获取 QApair 成功", {"items": results})
            else:
                items = self.service.get_all_pairs()
                return ApiResponse.success("获取 QApair 列表成功", {"items": items})
        except FileProcessingError as fpe:
            logger.error(f"QApair GET 错误: {fpe}")
            return ApiResponse.bad_request(str(fpe))
        except Exception:
            logger.exception("QApair GET 异常")
            return ApiResponse.internal_error("获取 QApair 信息失败")

    def post(self):
        try:
            if 'files' not in request.files:
                return ApiResponse.bad_request("没有上传文件")

            files = request.files.getlist('files')
            if not files:
                return ApiResponse.bad_request("没有上传文件")

            result = self.service.import_files(files)
            return ApiResponse.created("导入成功", result)

        except FileProcessingError as fpe:
            logger.error(f"QApair POST 校验失败: {fpe}")
            return ApiResponse.bad_request(str(fpe))
        except Exception:
            logger.exception("QApair POST 异常")
            return ApiResponse.internal_error("导入 QApair 失败")
    
    def put(self, qa_id: str = None):
        try:
            if not qa_id:
                return ApiResponse.bad_request("ID 不能为空")

            # 只支持单个ID更新
            try:
                qid = int(qa_id)
            except ValueError:
                return ApiResponse.bad_request("无效的QApair ID")

            payload = request.get_json(silent=True) or {}
            question = (payload.get("question") or "").strip()
            answer = (payload.get("answer") or "").strip()
            if not question:
                return ApiResponse.bad_request("question 不能为空")

            ok = self.service.update_pair(qid, question, answer)
            if not ok:
                return ApiResponse.not_found("QApair 不存在")

            # 返回更新后的实体
            item = self.service.get_pair_by_id(qid)
            return ApiResponse.success("更新成功", {"item": self._to_dict(item)})
        except FileProcessingError as fpe:
            logger.error(f"QApair PUT 错误: {fpe}")
            return ApiResponse.bad_request(str(fpe))
        except Exception:
            logger.exception("QApair PUT 异常")
            return ApiResponse.internal_error("更新 QApair 失败")
    def delete(self, qa_id: str = None):
        try:
            if not qa_id:
                return ApiResponse.bad_request("ID 不能为空")

            # 只支持单个ID删除
            try:
                qid = int(qa_id)
            except ValueError:
                return ApiResponse.bad_request("无效的QApair ID")

            ok = self.service.delete_pair(qid)
            if not ok:
                return ApiResponse.not_found("QApair 不存在")

            return ApiResponse.success("删除成功")

        except FileProcessingError as fpe:
            logger.error(f"QApair DELETE 错误: {fpe}")
            return ApiResponse.bad_request(str(fpe))
        except Exception:
            logger.exception("QApair DELETE 异常")
            return ApiResponse.internal_error("删除 QApair 失败")
