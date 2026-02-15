import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from fastapi import UploadFile
from typing import Optional, Dict, Tuple

# 配置Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


class CloudinaryService:
    """Cloudinary图片上传服务"""

    @staticmethod
    def get_folder(user: str) -> str:
        """生成用户文件夹路径"""
        return f"love_app/album/{user}"

    @staticmethod
    def generate_public_id(user: str, filename: str) -> str:
        """生成唯一的public_id"""
        import time
        import uuid

        # 移除文件扩展名
        name_without_ext = os.path.splitext(filename)[0]
        # 生成唯一ID：用户_时间戳_UUID
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"{user}_{timestamp}_{unique_id}_{name_without_ext}"

    @staticmethod
    async def upload_image(
            file: UploadFile,
            user: str,
            folder: str = "love_app/album"
    ) -> Dict:
        """
        上传图片到Cloudinary

        返回格式：
        {
            "success": True/False,
            "url": "图片URL",
            "public_id": "Cloudinary ID",
            "format": "jpg/png等",
            "width": 图片宽度,
            "height": 图片高度,
            "secure_url": "HTTPS链接"
        }
        """
        try:
            # 读取文件内容
            file_content = await file.read()

            # 验证文件大小（限制10MB）
            max_size = 10 * 1024 * 1024  # 10MB
            if len(file_content) > max_size:
                return {
                    "success": False,
                    "error": f"图片大小不能超过10MB（当前：{len(file_content) / 1024 / 1024:.2f}MB）"
                }

            # 验证文件类型
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
            if file.content_type not in allowed_types:
                return {
                    "success": False,
                    "error": f"不支持的文件类型，请使用: {', '.join(allowed_types)}"
                }

            # 生成public_id（云存储中的唯一标识）
            public_id = CloudinaryService.generate_public_id(user, file.filename)

            # 上传到Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_content,
                folder=CloudinaryService.get_folder(user),
                public_id=public_id,
                resource_type="image",
                overwrite=False,  # 不覆盖同名文件
                transformation=[
                    {"width": 1200, "height": 800, "crop": "limit"},  # 限制最大尺寸
                    {"quality": "auto:good"},  # 自动优化质量
                    {"fetch_format": "auto"}  # 自动选择最佳格式
                ]
            )

            return {
                "success": True,
                "url": upload_result.get("secure_url"),
                "public_id": upload_result.get("public_id"),
                "format": upload_result.get("format"),
                "width": upload_result.get("width"),
                "height": upload_result.get("height"),
                "bytes": upload_result.get("bytes"),
                "created_at": upload_result.get("created_at")
            }

        except cloudinary.exceptions.Error as e:
            return {
                "success": False,
                "error": f"Cloudinary上传失败: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"上传失败: {str(e)}"
            }

    @staticmethod
    def delete_image(public_id: str) -> Dict:
        """从Cloudinary删除图片"""
        try:
            result = cloudinary.uploader.destroy(public_id)
            if result.get("result") == "ok":
                return {
                    "success": True,
                    "message": "图片删除成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("result", "未知错误")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"删除失败: {str(e)}"
            }

    @staticmethod
    def get_image_url(public_id: str, width: int = None, height: int = None) -> str:
        """获取图片URL，支持尺寸调整"""
        if width and height:
            # 生成缩略图
            return cloudinary.utils.cloudinary_url(
                public_id,
                width=width,
                height=height,
                crop="fill",
                quality="auto"
            )[0]
        else:
            # 原始图片
            return cloudinary.utils.cloudinary_url(public_id)[0]

    @staticmethod
    def get_user_images(user: str, max_results: int = 100) -> list:
        """获取用户的所有图片"""
        try:
            result = cloudinary.api.resources(
                type="upload",
                prefix=f"love_app/album/{user}/",
                max_results=max_results,
                resource_type="image"
            )
            return result.get("resources", [])
        except Exception as e:
            print(f"获取用户图片失败: {e}")
            return []