"""
115目录树解析器，用于解析115导出的目录树文件
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
import chardet

from app.models.strm import FileType, SystemSettings


class TreeParser:
    """
    TreeParser类用于解析目录树和文件
    """

    def __init__(self, settings=None):
        """
        初始化解析器

        Args:
            settings: 系统设置对象，如果为None，则使用默认配置
        """
        # 初始化为空列表，不再使用默认配置
        self.video_extensions = []
        self.audio_extensions = []
        self.image_extensions = []
        self.subtitle_extensions = []
        self.metadata_extensions = []

        self.settings_version = 1  # 默认版本号

        # 如果提供了系统设置，则使用系统设置中的文件类型配置
        if settings:
            self._load_settings_from_db(settings)

        # 确保文件类型配置不为空，提供默认值
        # 如果视频文件类型为空，使用默认配置
        if not self.video_extensions:
            self.video_extensions = ["mkv", "mp4", "avi", "rmvb", "wmv", "mov", "m2ts", "ts", "iso", "flv"]

        # 如果音频文件类型为空，使用默认配置
        if not self.audio_extensions:
            self.audio_extensions = ["mp3", "flac", "wav", "aac", "ogg", "m4a", "wma"]

        # 如果图片文件类型为空，使用默认配置
        if not self.image_extensions:
            self.image_extensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"]

        # 如果字幕文件类型为空，使用默认配置
        if not self.subtitle_extensions:
            self.subtitle_extensions = ["srt", "ass", "ssa", "vtt", "sub", "idx"]

        # 如果元数据文件类型为空，使用默认配置
        if not self.metadata_extensions:
            self.metadata_extensions = ["nfo", "xml", "json", "txt"]

    def _load_settings_from_db(self, settings):
        """
        从系统设置中加载文件类型配置

        Args:
            settings: 系统设置对象或字典
        """
        if settings is None:
            return

        # 记录系统设置的版本号
        if isinstance(settings, dict):
            self.settings_version = settings.get("settings_version", 1)
        else:
            self.settings_version = getattr(settings, "settings_version", 1)

        # 获取原始设置值
        if isinstance(settings, dict):
            video_types_raw = settings.get("video_file_types")
            audio_types_raw = settings.get("audio_file_types")
            image_types_raw = settings.get("image_file_types")
            subtitle_types_raw = settings.get("subtitle_file_types")
            metadata_types_raw = settings.get("metadata_file_types")
        else:
            video_types_raw = getattr(settings, "video_file_types", None)
            audio_types_raw = getattr(settings, "audio_file_types", None)
            image_types_raw = getattr(settings, "image_file_types", None)
            subtitle_types_raw = getattr(settings, "subtitle_file_types", None)
            metadata_types_raw = getattr(settings, "metadata_file_types", None)

        # 视频文件类型
        video_types = video_types_raw or ""
        if video_types is None:
            video_types = ""
        self.video_extensions = [ext.strip() for ext in video_types.split(",") if ext.strip()]

        # 音频文件类型
        audio_types = audio_types_raw or ""
        if audio_types is None:
            audio_types = ""
        self.audio_extensions = [ext.strip() for ext in audio_types.split(",") if ext.strip()]

        # 图片文件类型
        image_types = image_types_raw or ""
        if image_types is None:
            image_types = ""
        self.image_extensions = [ext.strip() for ext in image_types.split(",") if ext.strip()]

        # 字幕文件类型
        subtitle_types = subtitle_types_raw or ""
        if subtitle_types is None:
            subtitle_types = ""
        self.subtitle_extensions = [ext.strip() for ext in subtitle_types.split(",") if ext.strip()]

        # 元数据文件类型
        metadata_types = metadata_types_raw or ""
        if metadata_types is None:
            metadata_types = ""
        self.metadata_extensions = [ext.strip() for ext in metadata_types.split(",") if ext.strip()]

    def _print_extensions(self):
        """打印当前的扩展名配置"""
        # 注释掉调试信息
        # print(f"[TreeParser] 当前文件类型配置 (版本: {self.settings_version}):")
        # print(f"  - 视频: {', '.join(self.video_extensions)}")
        # print(f"  - 音频: {', '.join(self.audio_extensions)}")
        # print(f"  - 图片: {', '.join(self.image_extensions)}")
        # print(f"  - 字幕: {', '.join(self.subtitle_extensions)}")
        # print(f"  - 元数据: {', '.join(self.metadata_extensions)}")
        pass

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析115导出的目录树文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的文件列表，每项包含文件路径、类型等信息
        """
        try:
            result = []
            current_path_stack = []

            # Detect file encoding
            with open(file_path, "rb") as f:
                raw_data = f.read()
                encoding_result = chardet.detect(raw_data)
                encoding = encoding_result["encoding"] or "utf-8"

            # Decode the file content and process line by line
            file_content = raw_data.decode(encoding)
            for line in file_content.splitlines():
                # 移除 BOM 和多余空白
                line = line.lstrip("\ufeff").rstrip()

                # 计算目录级别
                line_depth = line.count("|")

                # 获取当前项名称
                item_name = line.split("|-")[-1].strip()
                if not item_name:
                    continue

                # 维护路径栈
                while len(current_path_stack) > line_depth:
                    current_path_stack.pop()

                if len(current_path_stack) == line_depth:
                    if current_path_stack:
                        current_path_stack.pop()

                current_path_stack.append(item_name)

                # 构建完整路径
                full_path = "/" + "/".join(current_path_stack)

                # 检查是否为目录
                filename = os.path.basename(full_path)
                if "." not in filename:
                    continue

                # 格式化路径 (移除第一段路径)
                formatted_path = self._format_file_path(full_path)

                # 获取文件类型
                file_type, extension = self._get_file_type(filename)

                if file_type is not None:
                    result.append(
                        {
                            "path": formatted_path,
                            "file_type": file_type,
                            "extension": extension,
                            "file_name": filename,
                            "directory": os.path.dirname(formatted_path),
                        }
                    )

            return result
        except Exception as e:
            raise ValueError(f"解析115目录树文件失败: {str(e)}")

    def _format_file_path(self, file_path: str) -> str:
        """
        格式化文件路径，移除第一段路径（通常是"根目录/nas"等）

        Args:
            file_path: 原始文件路径

        Returns:
            格式化后的文件路径
        """
        first_slash = file_path.find("/")
        if first_slash != -1:
            second_slash = file_path.find("/", first_slash + 1)
            if second_slash != -1:
                return file_path[second_slash:]
        return file_path

    def _get_file_type(self, filename: str) -> Tuple[Optional[str], str]:
        """
        根据文件名判断文件类型

        Args:
            filename: 文件名

        Returns:
            (文件类型, 文件扩展名)
        """
        _, extension = os.path.splitext(filename)
        extension = extension.lower().lstrip(".")

        if extension in self.video_extensions:
            return FileType.VIDEO, extension
        elif extension in self.audio_extensions:
            return FileType.AUDIO, extension
        elif extension in self.image_extensions:
            return FileType.IMAGE, extension
        elif extension in self.subtitle_extensions:
            return FileType.SUBTITLE, extension
        elif extension in self.metadata_extensions:
            return FileType.METADATA, extension
        else:
            return FileType.OTHER, extension

    def filter_files(
        self,
        files: List[Dict[str, Any]],
        file_type: Optional[str] = None,
        keyword: Optional[str] = None,
        path_pattern: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据条件过滤文件

        Args:
            files: 文件列表
            file_type: 文件类型
            keyword: 关键词
            path_pattern: 路径模式

        Returns:
            过滤后的文件列表
        """
        result = files

        if file_type:
            result = [f for f in result if f["file_type"] == file_type]

        if keyword:
            result = [f for f in result if keyword.lower() in f["path"].lower()]

        if path_pattern:
            regex = re.compile(path_pattern)
            result = [f for f in result if regex.search(f["path"])]

        return result

    def get_file_type(self, file_path: str) -> str:
        """
        根据文件路径获取文件类型

        Args:
            file_path: 文件路径

        Returns:
            文件类型枚举值
        """
        if not file_path:
            return FileType.OTHER

        filename = os.path.basename(file_path)
        file_type, _ = self._get_file_type(filename)
        return file_type


async def parse_directory_tree(file_path: str, settings=None) -> List[Dict[str, Any]]:
    """
    解析115导出的目录树文件

    Args:
        file_path: 文件路径
        settings: 可选的系统设置对象，包含文件类型配置

    Returns:
        解析后的文件列表，每项包含文件路径、类型等信息
    """

    # 定义默认设置类
    class MockSettings:
        """模拟的系统设置类，当无法从数据库获取有效设置时使用"""

        def __init__(self):
            self.video_file_types = "mkv,mp4,avi,rmvb,wmv,mov,m2ts,ts,iso,flv"
            self.audio_file_types = "mp3,flac,wav,aac,ogg,m4a,wma"
            self.image_file_types = "jpg,jpeg,png,gif,bmp,tiff,webp"
            self.subtitle_file_types = "srt,ass,ssa,vtt,sub,idx"
            self.metadata_file_types = "nfo,xml,json,txt"
            self.settings_version = 1

            # 其他可能需要的属性
            self.enable_path_replacement = True
            self.replacement_path = "/nas"
            self.download_threads = 3
            self.output_directory = "strm_output"
            self.id = 0  # 模拟ID

    # 如果未提供系统设置，尝试从数据库获取
    if settings is None:
        try:
            from app.models.strm import SystemSettings
            from tortoise.queryset import QuerySet

            print("[调试日志] 尝试从数据库获取系统设置")

            # 直接尝试获取所有记录
            settings_list = await SystemSettings.all()
            if settings_list and len(settings_list) > 0:
                # 使用第一条记录
                settings = settings_list[0]
                print(f"[调试日志] 成功获取系统设置实例: ID={settings.id}, 类型={type(settings)}")
            else:
                # 没有记录，使用模拟设置
                print("[调试日志] 数据库中没有系统设置记录，使用模拟设置")
                settings = MockSettings()
                print(f"[调试日志] 创建了模拟设置: {type(settings)}")

                # 尝试创建系统设置记录
                try:
                    print("[调试日志] 尝试在数据库中创建默认系统设置记录")
                    db_settings = await SystemSettings.create(
                        video_file_types=settings.video_file_types,
                        audio_file_types=settings.audio_file_types,
                        image_file_types=settings.image_file_types,
                        subtitle_file_types=settings.subtitle_file_types,
                        metadata_file_types=settings.metadata_file_types,
                        enable_path_replacement=settings.enable_path_replacement,
                        replacement_path=settings.replacement_path,
                        download_threads=settings.download_threads,
                        output_directory=settings.output_directory,
                        settings_version=1,
                    )
                    print(f"[调试日志] 成功创建系统设置记录，ID: {db_settings.id}")
                except Exception as create_error:
                    print(f"[调试日志] 创建系统设置记录失败: {str(create_error)}")
        except Exception as e:
            print(f"[调试日志] 获取系统设置失败: {str(e)}")
            import traceback

            print(f"[调试日志] 获取系统设置异常详情: {traceback.format_exc()}")
            # 使用模拟设置
            settings = MockSettings()
            print(f"[调试日志] 由于异常，使用模拟设置: {type(settings)}")

    # 检查settings是否为QuerySet类型
    from tortoise.queryset import QuerySet

    if isinstance(settings, QuerySet):
        print("[调试日志] 收到QuerySet类型的设置对象，转换为模拟设置")
        settings = MockSettings()
        print(f"[调试日志] 转换后的模拟设置类型: {type(settings)}")

    # 如果settings为None，使用模拟设置
    if settings is None:
        print("[调试日志] 设置对象为None，使用模拟设置")
        settings = MockSettings()

    # 创建解析器实例，传入系统设置
    print(f"[调试日志] 创建TreeParser实例，设置对象类型: {type(settings)}")
    parser = TreeParser(settings)
    return parser.parse_file(file_path)


def parse_directory_tree_sync(file_path: str, settings=None) -> List[Dict[str, Any]]:
    """
    同步解析115导出的目录树文件，适用于不能使用异步函数的场合

    Args:
        file_path: 文件路径
        settings: 可选的系统设置对象，包含文件类型配置

    Returns:
        解析后的文件列表，每项包含文件路径、类型等信息
    """
    # 注意：此函数不会从数据库获取系统设置，因为它是同步函数
    # 如果需要使用系统设置，调用者应该先获取系统设置并传入
    parser = TreeParser(settings)
    return parser.parse_file(file_path)


async def test_file_type_detection():
    """
    用于测试文件类型检测的函数
    此函数展示如何根据系统设置正确识别文件类型
    """

    # 创建一个模拟的系统设置对象
    class MockSettings:
        def __init__(self):
            self.video_file_types = "mkv,mp4"
            self.audio_file_types = "mp3,wav"
            self.image_file_types = "jpg,png"
            self.subtitle_file_types = "srt,ass"
            self.metadata_file_types = "xml,json"  # 默认NFO不在元数据中

    # 测试 1: 使用空配置（没有默认配置）
    parser1 = TreeParser()
    nfo_type1, _ = parser1._get_file_type("movie.nfo")
    # print(f"空配置下，.nfo文件类型为: {nfo_type1}")  # 应该是 "other"，因为没有默认配置

    # 测试 2: 使用自定义配置，将NFO配置为元数据类型
    settings2 = MockSettings()
    settings2.metadata_file_types = "nfo,xml,json"
    parser2 = TreeParser(settings2)
    nfo_type2, _ = parser2._get_file_type("movie.nfo")
    # print(f"将NFO配置为元数据时，.nfo文件类型为: {nfo_type2}")  # 应该是 "metadata"

    # 测试 3: 使用自定义配置，将NFO配置为字幕类型
    settings3 = MockSettings()
    settings3.subtitle_file_types = "nfo,srt,ass"  # NFO作为字幕类型
    settings3.metadata_file_types = "xml,json"  # 元数据中不包含NFO
    parser3 = TreeParser(settings3)
    nfo_type3, _ = parser3._get_file_type("movie.nfo")
    # print(f"将NFO配置为字幕时，.nfo文件类型为: {nfo_type3}")  # 应该是 "subtitle"

    # 测试 4: 使用不完整配置（某些类别可能为空）
    settings4 = MockSettings()
    settings4.video_file_types = "mkv,mp4"
    settings4.audio_file_types = ""  # 空音频类型
    settings4.image_file_types = "jpg,png"
    settings4.subtitle_file_types = "srt,ass"
    settings4.metadata_file_types = ""  # 空元数据类型
    parser4 = TreeParser(settings4)
    mp3_type, _ = parser4._get_file_type("music.mp3")
    nfo_type4, _ = parser4._get_file_type("movie.nfo")
    # print(f"不完整配置下，.mp3文件类型为: {mp3_type}")  # 应该是 "other"，因为audio_file_types为空
    # print(f"不完整配置下，.nfo文件类型为: {nfo_type4}")  # 应该是 "other"，因为不在任何配置中

    return {
        "empty_config_nfo_type": nfo_type1,
        "metadata_nfo_type": nfo_type2,
        "subtitle_nfo_type": nfo_type3,
        "incomplete_config_nfo_type": nfo_type4,
    }


def update_file_types(files: List[Dict[str, Any]], settings=None) -> List[Dict[str, Any]]:
    """
    根据当前系统设置动态更新文件类型

    Args:
        files: 文件列表，每个文件必须包含"extension"或"path"/"file_name"字段
        settings: 系统设置对象，包含文件类型配置

    Returns:
        更新了文件类型的文件列表
    """
    if not files:
        return files

    # 创建解析器实例
    parser = TreeParser(settings)

    # 更新文件类型
    updated_files = []
    for file in files:
        # 确保文件对象可以被修改
        file = dict(file)

        # 获取扩展名
        extension = None
        if "extension" in file:
            extension = file["extension"]
        elif "path" in file or "file_name" in file:
            # 从文件路径或文件名中获取扩展名
            file_name = file.get("file_name") or os.path.basename(file.get("path", ""))
            _, extension = os.path.splitext(file_name)
            extension = extension[1:] if extension else ""  # 移除前导点号

        if extension:
            # 重新检测文件类型
            file_type, _ = parser._get_file_type(f"file.{extension}")

            # 只有在文件类型不同时才更新
            if file.get("file_type") != file_type:
                # 移除调试信息
                # print(
                #     f"文件类型已更新: {file.get('file_name', file.get('path', 'unknown'))} 从 {file.get('file_type', 'unknown')} 到 {file_type}"
                # )
                file["file_type"] = file_type
                file["updated_type"] = True  # 标记已更新

        updated_files.append(file)

    return updated_files


async def check_and_update_parse_result(record, settings=None):
    """
    检查解析结果的设置版本号，如果与当前系统设置版本号不匹配，则更新解析结果中的文件类型

    Args:
        record: 上传记录对象，包含解析结果
        settings: 当前系统设置对象，如果为None则会尝试从数据库获取

    Returns:
        tuple: (是否更新, 更新后的解析结果)
    """
    # 如果设置为None，尝试从数据库获取
    if settings is None:
        from app.models.strm import SystemSettings

        settings = await SystemSettings.all().first()
        if not settings:
            # print("未找到系统设置，无法进行版本检查")
            return False, record.parsed_result

    # 获取当前系统设置版本号
    current_version = settings.settings_version

    # 检查解析结果中是否包含设置版本号
    parsed_result = record.parsed_result
    result_version = parsed_result.get("settings_version")

    # 如果版本号相同或解析结果中没有文件列表，则不需要更新
    if result_version == current_version or "parsed_files" not in parsed_result:
        return False, parsed_result

    # print(f"检测到系统设置版本变更 (结果版本: {result_version}, 当前版本: {current_version})，更新解析结果中的文件类型")

    # 动态更新文件类型
    updated_files = update_file_types(parsed_result["parsed_files"], settings)

    # 统计更新的文件数量
    updated_count = len([f for f in updated_files if f.get("updated_type", False)])

    if updated_count > 0:
        # 更新统计信息
        stats = {
            "total": len(updated_files),
            "video": len([f for f in updated_files if f["file_type"] == "video"]),
            "audio": len([f for f in updated_files if f["file_type"] == "audio"]),
            "image": len([f for f in updated_files if f["file_type"] == "image"]),
            "subtitle": len([f for f in updated_files if f["file_type"] == "subtitle"]),
            "metadata": len([f for f in updated_files if f["file_type"] == "metadata"]),
            "other": len([f for f in updated_files if f["file_type"] == "other"]),
        }

        # 创建更新后的解析结果
        updated_result = dict(parsed_result)
        updated_result["parsed_files"] = updated_files
        updated_result["stats"] = stats
        updated_result["settings_version"] = current_version

        # 将更新后的解析结果保存回数据库
        record.parsed_result = updated_result
        await record.save()

        # print(f"已更新解析结果中的 {updated_count} 个文件的类型并保存到数据库")
        return True, updated_result
    else:
        # 虽然版本号不同，但没有文件类型变化，仅更新版本号
        parsed_result["settings_version"] = current_version
        record.parsed_result = parsed_result
        await record.save()
        # print("系统设置版本已更新，但没有文件类型变化")
        return False, parsed_result
