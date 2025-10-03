import json
import logging
import sys
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Any, Optional, List, Tuple
from threading import Lock
from tqdm import tqdm  # 导入进度条库

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_processor_function(processor_path: str) -> Callable[[Dict[str, Any]], Dict[str, Any] | List[Dict[str, Any]]]:
    """
    从指定文件动态加载processor函数

    :param processor_path: 处理器函数路径，格式为"文件路径:函数名"
    :return: 加载的处理器函数，可返回单个字典或字典列表
    """
    try:
        # 分割文件路径和函数名
        file_path, func_name = processor_path.split(':', 1)
        file_path = file_path.strip()
        func_name = func_name.strip()

        # 检查文件是否存在
        if not Path(file_path).exists():
            raise FileNotFoundError(f"处理器文件不存在: {file_path}")

        # 动态导入模块
        spec = importlib.util.spec_from_file_location("processor_module", file_path)
        if spec is None:
            raise ImportError(f"无法从文件创建模块规范: {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore

        # 获取函数
        processor_func = getattr(module, func_name, None)
        if processor_func is None or not callable(processor_func):
            raise AttributeError(f"在文件 {file_path} 中未找到可调用的函数 {func_name}")

        logger.info(f"成功从 {file_path} 加载处理器函数 {func_name}")
        return processor_func

    except Exception as e:
        logger.error(f"加载处理器函数失败: {str(e)}")
        raise

class OrderedJSONLProcessor:
    """保持输入输出顺序和行数一致的JSONL处理器"""

    def __init__(self,
                 process_func: Callable[[Dict[str, Any]], Dict[str, Any] | List[Dict[str, Any]]],
                 error_handler: Optional[Callable[[Dict[str, Any], Exception], Dict[str, Any]]] = None):
        """
        初始化处理器

        :param process_func: 处理单行JSON的函数，可返回单个字典或字典列表
        :param error_handler: 错误处理函数，必须返回一个值以保持行数
        """
        self.process_func = process_func
        # 确保错误处理函数返回值，维持行数
        self.error_handler = error_handler or self._default_error_handler
        self.write_lock = Lock()  # 保证写入线程安全
        self.results: Dict[int, Optional[List[str]]] = {}  # 存储处理结果，按索引排序，每个结果可能包含多行
        self.next_write_index = 0  # 下一个要写入的索引

    @staticmethod
    def _default_error_handler(data: Dict[str, Any], exc: Exception) -> Dict[str, Any]:
        """默认错误处理器，返回包含错误信息的数据"""
        logger.error(f"处理数据出错: {str(exc)}, 数据: {data}")
        return {"_error": str(exc), "_original_data": data}

    def _process_with_index(self, line: str, index: int, progress_bar: tqdm, output_stream) -> None:
        """处理带索引的行，并在合适时机写入结果"""
        try:
            if not line.strip():  # 处理空行
                result_lines = [""]
            else:
                data = json.loads(line.strip())
                processed = self.process_func(data)

                # 根据处理结果的类型生成不同的输出行
                if isinstance(processed, list):
                    # 对于字典列表，每个元素生成一行
                    result_lines = [
                        json.dumps(item, ensure_ascii=False)
                        for item in processed
                        if isinstance(item, dict)
                    ]
                    # 过滤空列表情况 - 修改为不写入任何行
                    if not result_lines:
                        result_lines = None
                elif isinstance(processed, dict):
                    # 对于单个字典，生成一行
                    result_lines = [json.dumps(processed, ensure_ascii=False)]
                elif processed is None:
                    # 返回None时不写入任何行
                    result_lines = None
                else:
                    # 对于其他类型，视为无效并记录警告
                    logger.warning(f"处理器返回无效类型 {type(processed)}，行号: {index+1}")
                    result_lines = [""]
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}, 行号: {index+1}")
            result_lines = [json.dumps({"_parse_error": str(e), "_original_line": line.strip()})]
        except Exception as e:
            # 调用错误处理器并确保返回值
            error_result = self.error_handler(data, e)
            result_lines = [json.dumps(error_result, ensure_ascii=False)]

        # 保存结果
        with self.write_lock:
            self.results[index] = result_lines
            progress_bar.update(1)

            # 检查是否可以写入连续的结果
            self._write_available_results(output_stream)

    def _write_available_results(self, output_stream) -> None:
        """写入所有连续可用的结果"""
        while self.next_write_index in self.results:
            result_lines = self.results[self.next_write_index]
            if result_lines:
                # 写入当前索引对应的所有行
                for line in result_lines:
                    output_stream.write(f"{line}\n")
            # 移除已写入的结果以节省内存
            del self.results[self.next_write_index]
            self.next_write_index += 1

    def process_stream(self,
                      input_stream,
                      output_stream,
                      max_workers: int = 4,
                      debug: bool = False,
                      total_lines: Optional[int] = None):
        """
        流式处理并保持顺序，实时写入结果

        :param input_stream: 输入流
        :param output_stream: 输出流
        :param max_workers: 并发工作线程数
        :param debug: 是否开启调试模式，禁用线程池
        :param total_lines: 总行数，用于进度条显示
        """
        # 计算总行数（如果未提供）
        if total_lines is None:
            logger.info("正在计算总行数...")
            # 保存当前位置以便后续重置
            current_pos = input_stream.tell()
            total_lines = sum(1 for _ in input_stream)
            # 重置到初始位置
            input_stream.seek(current_pos)
            logger.info(f"总行数: {total_lines}")

        # 创建进度条
        progress_bar = tqdm(total=total_lines, desc="处理进度", unit="行")

        if debug:
            logger.info("开启调试模式，禁用线程池，将按顺序处理")
        else:
            logger.info(f"开始处理，并发数: {max_workers}，保持输入输出顺序")

        if debug:
            # 调试模式：不使用线程池，顺序处理
            index = 0
            while True:
                line = input_stream.readline()
                if not line:
                    break  # 读取完毕
                # 直接处理并立即写入
                self._process_with_index(line, index, progress_bar, output_stream)
                index += 1
        else:
            # 正常模式：使用线程池
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                index = 0
                while True:
                    line = input_stream.readline()
                    if not line:
                        break  # 读取完毕
                    # 提交任务时带上索引和输出流
                    executor.submit(
                        self._process_with_index,
                        line,
                        index,
                        progress_bar,
                        output_stream
                    )
                    index += 1

        # 等待所有结果处理完毕并写入
        while self.next_write_index < total_lines:
            with self.write_lock:
                self._write_available_results(output_stream)

        # 关闭进度条
        progress_bar.close()
        logger.info(f"处理完成，总处理输入行数: {self.next_write_index}")

# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any] | List[Dict[str, Any]]:
    """示例：转换键为小写，演示既可以返回单个字典也可以返回字典列表"""
    lower_data = {k.lower(): v for k, v in data.items()}

    # 演示：如果有"items"键且值为列表，则返回多个结果
    if "items" in lower_data and isinstance(lower_data["items"], list):
        return [{"original_id": lower_data.get("id"), "item": item} for item in lower_data["items"]]

    return lower_data

# 命令行使用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='保持顺序的JSONL处理工具，支持返回列表生成多行')
    parser.add_argument('--input', type=str, help='输入JSONL文件路径，默认stdin')
    parser.add_argument('--output', type=str, help='输出JSONL文件路径，默认stdout')
    parser.add_argument('--workers', type=int, default=4, help='并发工作数')
    parser.add_argument('--debug', action='store_true', help='开启调试模式，禁用线程池')
    parser.add_argument('--processor', type=str, help='处理器函数路径，格式为"文件路径:函数名"，默认使用内置示例函数')
    parser.add_argument('--total-lines', type=int, help='总行数，用于进度条显示，不指定则自动计算')

    args = parser.parse_args()

    # 确保在使用标准输入时不尝试计算行数（会导致阻塞）
    if args.input is None and args.total_lines is None:
        logger.warning("从标准输入读取时无法自动计算行数，进度条将无法准确显示。请使用--total-lines参数指定总行数以获得准确进度。")

    # 加载处理器函数
    if args.processor:
        process_func = load_processor_function(args.processor)
    else:
        process_func = example_processor
        logger.info("使用内置示例处理器函数")

    # 打开输入输出流
    with (open(args.input, 'r', encoding='utf-8') if args.input else sys.stdin) as infile, \
         (open(args.output, 'w', encoding='utf-8') if args.output else sys.stdout) as outfile:

        processor = OrderedJSONLProcessor(process_func)
        processor.process_stream(
            infile,
            outfile,
            max_workers=args.workers,
            debug=args.debug,
            total_lines=args.total_lines
        )
