# test_env.py
import os
from pathlib import Path
from dotenv import load_dotenv


def test_env_variables():
    """测试环境变量加载"""

    print("🔍 当前工作目录:", os.getcwd())
    print("🔍 检查 .env 文件...")

    # 1. 尝试不同位置的 .env 文件
    env_paths = [
        Path(".env"),  # 当前目录
        Path("../.env"),  # 上级目录
        Path("./.env"),  # 当前目录（另一种写法）
        Path(__file__).parent / ".env",  # 脚本所在目录
    ]

    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            print(f"✅ 找到 .env 文件: {env_path.absolute()}")
            # 加载 .env 文件
            load_dotenv(dotenv_path=env_path)
            env_loaded = True
            break

    if not env_loaded:
        print("❌ 没有找到 .env 文件")
        print("尝试手动指定 .env 路径...")
        # 手动指定路径
        manual_path = "D:/codepro/fastapi_love/.env"
        if os.path.exists(manual_path):
            load_dotenv(dotenv_path=manual_path)
            print(f"✅ 从手动路径加载: {manual_path}")
        else:
            print("❌ 手动路径也不存在")
            print("请在以下位置创建 .env 文件:")
            print("D:\\codepro\\fastapi_love\\.env")

    # 2. 检查环境变量
    print("\n🔍 检查环境变量...")

    env_vars = {
        "CLOUDINARY_CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "CLOUDINARY_API_KEY": os.getenv("CLOUDINARY_API_KEY"),
        "CLOUDINARY_API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "PORT": os.getenv("PORT"),
        "DATABASE_URL": os.getenv("DATABASE_URL")
    }

    all_good = True
    for key, value in env_vars.items():
        if value:
            print(f"✅ {key}: 已设置（{value[:10]}...）" if len(str(value)) > 10 else f"✅ {key}: {value}")
        else:
            print(f"❌ {key}: 未设置")
            all_good = False

    # 3. 打印所有环境变量（排除敏感信息）
    print("\n🔍 当前所有环境变量:")
    for key, value in os.environ.items():
        if key.startswith("CLOUDINARY") or key in ["SECRET_KEY", "DATABASE_URL"]:
            masked = value[:4] + "****" + value[-4:] if value and len(value) > 8 else "****"
            print(f"  {key}: {masked}")

    return all_good


def check_cloudinary():
    """测试Cloudinary配置"""
    print("\n🔍 测试Cloudinary配置...")

    try:
        import cloudinary

        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        if not all([cloud_name, api_key, api_secret]):
            print("❌ Cloudinary环境变量未设置完整")
            return False

        # 配置Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        print("✅ Cloudinary配置成功")

        # 测试连接（ping）
        import cloudinary.api
        result = cloudinary.api.ping()
        if result.get("status") == "ok":
            print("✅ Cloudinary连接测试通过")
            return True
        else:
            print("❌ Cloudinary连接测试失败")
            return False

    except ImportError:
        print("❌ 未安装cloudinary库，运行: pip install cloudinary")
        return False
    except Exception as e:
        print(f"❌ Cloudinary测试失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("环境变量测试脚本")
    print("=" * 50)

    # 测试环境变量
    if test_env_variables():
        print("\n✅ 环境变量测试通过")

        # 测试Cloudinary
        if check_cloudinary():
            print("\n🎉 所有测试通过！可以上传图片到Cloudinary了！")
        else:
            print("\n⚠️ Cloudinary测试失败，请检查API密钥")
    else:
        print("\n❌ 环境变量测试失败，请检查 .env 文件")

    print("\n💡 提示：")
    print("1. 确保 .env 文件在项目根目录")
    print("2. .env 文件格式：KEY=VALUE（不要有空格）")
    print("3. 不要提交 .env 文件到GitHub！")
    print("4. 在Render控制台设置相同的环境变量")