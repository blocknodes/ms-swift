from typing import Callable, Dict, Any, Optional, List, Tuple
import os

import json
from typing import List, Dict, Union

def search_jsonl(
    file_path: str,
    target_key: str,
    target_value: str,
    case_sensitive: bool = True
) -> List[Dict]:
    """
    读取 JSONL 文件，筛选出指定 key 包含指定 value 的行
    :param file_path: JSONL 文件路径
    :param target_key: 要检查的键名
    :param target_value: 要匹配的内容（字符串包含）
    :param case_sensitive: 是否区分大小写（默认区分）
    :return: 符合条件的 JSON 字典列表
    """
    matched_lines = []

    # 逐行读取文件（避免大文件加载到内存）
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:  # 跳过空行
                continue

            try:
                # 解析 JSON 行为字典
                json_obj = json.loads(line)

                # 检查目标 key 是否存在
                if target_key not in json_obj:
                    continue

                # 获取 key 对应的值，并处理大小写
                value = json_obj[target_key]
                if not case_sensitive:
                    # 统一转为小写（仅针对字符串）
                    if isinstance(value, str):
                        value = value.lower()
                        target_value = target_value.lower()

                # 判断值是否包含目标内容（支持字符串/列表两种常见场景）
                match = False
                if isinstance(value, str):
                    # 场景1：值是字符串，检查子串包含
                    match = target_value in value
                elif isinstance(value, list):
                    # 场景2：值是列表，检查元素包含
                    match = target_value in value
                else:
                    # 其他类型（数字/布尔等），直接等值匹配
                    match = (value == target_value)

                if match:
                    # 可选：添加行号便于定位
                    json_obj["_line_num"] = line_num
                    matched_lines.append(json_obj)

            except json.JSONDecodeError as e:
                print(f"警告：第 {line_num} 行 JSON 解析失败 → {e}")
            except Exception as e:
                print(f"错误：处理第 {line_num} 行时出错 → {e}")

    return matched_lines

# ------------------- 测试示例 -------------------
if __name__ == "__main__":
    # 假设 test.jsonl 内容如下：
    # {"model": "iPhone 14 Pro", "params": ["6.1英寸", "A16芯片"]}
    # {"model": "iPhone 15", "params": ["6.2英寸", "A17芯片"]}
    # {"model": "Mate 60 Pro", "params": ["6.8英寸", "麒麟9000s"]}

    # 搜索 "model" 包含 "iPhone 14" 的行
    results = search_jsonl(
        file_path="test.jsonl",
        target_key="model",
        target_value="iPhone 14",
        case_sensitive=False  # 不区分大小写
    )

    # 输出结果
    print(f"找到 {len(results)} 条匹配结果：")
    for res in results:
        print(f"行号：{res['_line_num']} → 内容：{res}")

# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    new_data={}
    new_data['query'] = data['query']
    #import pdb;pdb.set_trace()
    # 处理pos列表
    query = new_data['query']
    llm_judge_file = os.getenv("LLM_JUDE_FILE")
    threshold = os.getenv("LLM_JUDE_THRESHOLD")
    #import pdb;pdb.set_trace()
    candidates = data['segments']

    results = search_jsonl(
        file_path=llm_judge_file,
        target_key="query",
        target_value=query,
        case_sensitive=True  # 不区分大小写
    )

    llm_result = results[0]

    pos =[]
    neg =[]
    for idx, item in enumerate(candidates):
        for item1 in llm_result['finals']:
            if item==item1['content']:
                if item1['llm_judge_score'] >= int(threshold):
                    pos.append({'content':item, 'score':10-idx/10,'llm_judge_score':item1['llm_judge_score']})
                else:
                    neg.append({'content':item, 'score':10-idx/10,'llm_judge_score':item1['llm_judge_score']})
                break

    new_data['pos'] = pos
    new_data['neg'] = neg

    return new_data