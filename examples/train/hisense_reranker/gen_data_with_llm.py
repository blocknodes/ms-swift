import json
import argparse
import requests
import time
import random
import os
from typing import Dict
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# 多个LLM配置选项
LLM_CONFIGS = {
    "deepseek-v3": {
        "url": "http://10.18.217.60:30264/xinghai-aliyun-ds-v3/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer {key}"
        },
        "key": "",
        "model": "deepseek-v3",
        "url_params": {}
    },
    "gpt-4": {
        "url": "https://inner-apisix.hisense.com/openai/deployments/gpt-4-1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "api-key": "Oi4rzFyLbMOmqVn8YYEyT2Pt0mkr3lgU"
        },
        "key": "nregzh6g2oviajyjstgzlhjsjmp9rtql",  # user_key参数
        "model": "gpt-4-1",
        "url_params": {
            "user_key": "{key}"  # URL中的参数
        }
    }
}

def get_qna_prompt(query: str, block: str, source: str) -> str:
    """构建用于Q&A类型内容相关性判断的提示词"""
    return f"""你是一名信息检索与问答领域的专家。请你从问答匹配的角度，严格按照以下标准判断用户问题与Q&A对的相关性：

相关性判定标准
- Q&A对的问题与用户问题高度相似，判定为“相关”，结果为 1。
- Q&A对的问题与用户问题不相关，或答案无法直接或间接回答问题，仅为表层词汇相关，判定为“不相关”，结果为 0。

请综合考虑以下维度：
1. 问题匹配度：Q&A对的问题与用户问题的语义相似度和意图一致性
2. 领域一致性：是否属于同一业务领域或应用场景
3. 排除表层词汇匹配：仅词汇相同但实际语义无关的，判为不相关

输入：
用户问题（query）：{query}
Q&A标题：{source}


请将你的相关性评分以如下严格的 JSON 格式输出，无需其他说明，示例：
{{"is_relevant": 0, "reason": "xxx"}}
    """

def get_doc_prompt(query: str, block: str, source: str) -> str:
    """构建用于文档片段相关性判断的提示词"""
    return f"""你是一名信息检索与文档理解领域的专家。请你从文档内容与查询匹配的角度，严格按照以下标准判断用户问题与文档片段及其来源的相关性：

相关性判定标准
- 文档片段结合文件名，能直接回答用户问题，或为问题提供明确的查询路径、操作方法、关键线索，判定为“相关”，结果为 1。
- 文档片段结合文件名，无法直接或间接回答问题，或仅为表层词汇相关、无实质信息支持，判定为“不相关”，结果为 0。

请综合考虑以下维度：
1. 信息覆盖度：文档片段内容是否覆盖用户问题的核心要点
2. 参考价值：能否为回答问题提供事实、数据、证据或有用线索
3. 上下文匹配：文档主题与用户问题是否属于同一领域或场景
4. 文件名辅助判断：文件名可辅助判断相关性，但不是唯一依据
5. 排除无关信息：与问题无关的流程、政策、其他产品信息判为不相关

输入：
用户问题（query）：{query}
文档片段：{block}
文档来源：{source}

请将你的相关性评分以如下严格的 JSON 格式输出，无需其他说明，示例：
{{"is_relevant": 0, "reason": "xxx"}}
    """

def create_llm_request_payload(llm_name: str, prompt: str) -> Dict:
    """创建LLM API请求的 payload"""
    if llm_name not in LLM_CONFIGS:
        raise ValueError(f"未知的LLM模型: {llm_name}")

    config = LLM_CONFIGS[llm_name]
    return {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "n": 1,  # 控制返回结果数量
        "temperature": 0  # 控制输出随机性
    }

def prepare_llm_request_parameters(llm_name: str) -> tuple:
    """准备LLM API请求的URL和 headers"""
    if llm_name not in LLM_CONFIGS:
        raise ValueError(f"未知的LLM模型: {llm_name}")

    config = LLM_CONFIGS[llm_name].copy()

    # 处理URL参数
    url_params = config["url_params"]
    if url_params:
        formatted_params = {k: v.format(key=config["key"]) for k, v in url_params.items()}
        query_string = "&".join([f"{k}={v}" for k, v in formatted_params.items()])
        request_url = f"{config['url']}?{query_string}"
    else:
        request_url = config["url"]

    # 处理请求头
    headers = {k: v.format(key=config["key"]) for k, v in config["headers"].items()}

    return request_url, headers

def parse_llm_response(response_text: str, query: str, block: str, source: str, llm_name: str,
                      content_type: str, line_number: int, item_index: int, verbose: bool) -> Dict[str, any]:
    """解析LLM返回的响应内容，增加额外元数据"""
    try:
        if verbose:
            print("\n===== LLM原始响应 =====")
            print(response_text)
            print("=======================\n")

        result = json.loads(response_text)

        if "is_relevant" in result and "reason" in result:
            if result["is_relevant"] not in (0, 1):
                parsed_result = {
                    "is_relevant": -1,
                    "reason": f"LLM返回的is_relevant值无效: {response_text}",
                    "query": query,
                    "block": block,
                    "source": source,
                    "llm_used": llm_name,
                    "content_type": content_type,
                    "line_number": line_number,
                    "item_index": item_index,
                    "raw_response": response_text
                }
            else:
                parsed_result = {** result,
                    "query": query,
                    "block": block,
                    "source": source,
                    "llm_used": llm_name,
                    "content_type": content_type,
                    "line_number": line_number,
                    "item_index": item_index,
                    "raw_response": response_text
                }
            return parsed_result
        else:
            return {
                "is_relevant": -1,
                "reason": f"LLM返回格式不正确: {response_text}",
                "query": query,
                "block": block,
                "source": source,
                "llm_used": llm_name,
                "content_type": content_type,
                "line_number": line_number,
                "item_index": item_index,
                "raw_response": response_text
            }
    except json.JSONDecodeError:
        return {
            "is_relevant": -1,
            "reason": f"无法解析LLM返回的JSON: {response_text}",
            "query": query,
            "block": block,
            "source": source,
            "llm_used": llm_name,
            "content_type": content_type,
            "line_number": line_number,
            "item_index": item_index,
            "raw_response": response_text
        }

def judge_relevance_with_llm(query: str, block: str, source: str, llm_name: str, content_type: str,
                           line_number: int, item_index: int, llm_log_path: str, verbose: bool,
                           max_retries: int = 3, initial_delay: float = 1.0) -> Dict[str, any]:
    """使用指定的LLM判断相关性，并将结果写入日志文件"""
    try:
        if content_type == "qna":
            prompt = get_qna_prompt(query, block, source)
        elif content_type == "doc":
            prompt = get_doc_prompt(query, block, source)
        else:
            raise ValueError(f"未知的内容类型: {content_type}")

        payload = create_llm_request_payload(llm_name, prompt)
        request_url, headers = prepare_llm_request_parameters(llm_name)

        # 退火重试机制
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    request_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    response_data = response.json()
                    llm_output = response_data["choices"][0]["message"]["content"].strip()
                    result = parse_llm_response(
                        llm_output, query, block, source, llm_name,
                        content_type, line_number, item_index, verbose
                    )
                    # 写入LLM日志
                    with open(llm_log_path, 'a', encoding='utf-8') as log_file:
                        json.dump(result, log_file, ensure_ascii=False)
                        log_file.write('\n')
                        log_file.flush()
                    return result
                else:
                    if attempt < max_retries:
                        if verbose:
                            reason = f"API请求失败 (状态码: {response.status_code})，将重试 (尝试 {attempt + 1}/{max_retries})"
                            print(f"{reason}: {response.text[:100]}...")
                    else:
                        error_result = {
                            "is_relevant": -1,
                            "reason": f"API请求失败，状态码: {response.status_code}, 响应: {response.text}",
                            "query": query,
                            "block": block,
                            "source": source,
                            "llm_used": llm_name,
                            "content_type": content_type,
                            "line_number": line_number,
                            "item_index": item_index,
                            "raw_response": response.text
                        }
                        with open(llm_log_path, 'a', encoding='utf-8') as log_file:
                            json.dump(error_result, log_file, ensure_ascii=False)
                            log_file.write('\n')
                            log_file.flush()
                        return error_result

            except Exception as e:
                if attempt < max_retries:
                    if verbose:
                        reason = f"调用LLM时发生错误，将重试 (尝试 {attempt + 1}/{max_retries})"
                        print(f"{reason}: {str(e)}")
                else:
                    error_result = {
                        "is_relevant": -1,
                        "reason": f"调用LLM时发生错误: {str(e)}",
                        "query": query,
                        "block": block,
                        "source": source,
                        "llm_used": llm_name,
                        "content_type": content_type,
                        "line_number": line_number,
                        "item_index": item_index,
                        "raw_response": str(e)
                    }
                    with open(llm_log_path, 'a', encoding='utf-8') as log_file:
                        json.dump(error_result, log_file, ensure_ascii=False)
                        log_file.write('\n')
                        log_file.flush()
                    return error_result

            # 退火延迟
            if attempt < max_retries:
                delay = initial_delay * (2 **attempt) + random.uniform(0, 0.5 * initial_delay * (2** attempt))
                if verbose:
                    print(f"等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)

        final_result = {
            "is_relevant": -1,
            "reason": "达到最大重试次数",
            "query": query,
            "block": block,
            "source": source,
            "llm_used": llm_name,
            "content_type": content_type,
            "line_number": line_number,
            "item_index": item_index,
            "raw_response": "达到最大重试次数"
        }
        with open(llm_log_path, 'a', encoding='utf-8') as log_file:
            json.dump(final_result, log_file, ensure_ascii=False)
            log_file.write('\n')
            log_file.flush()
        return final_result

    except ValueError as e:
        error_result = {
            "is_relevant": -1,
            "reason": str(e),
            "query": query,
            "block": block,
            "source": source,
            "llm_used": llm_name,
            "content_type": content_type,
            "line_number": line_number,
            "item_index": item_index,
            "raw_response": str(e)
        }
        with open(llm_log_path, 'a', encoding='utf-8') as log_file:
            json.dump(error_result, log_file, ensure_ascii=False)
            log_file.write('\n')
            log_file.flush()
        return error_result

def count_jsonl_lines(file_path):
    """计算JSONL文件中的行数（非空行）"""
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1
    return count

def process_line(line, line_number, llm_name, llm_log_path, output_file_path, verbose):
    """处理单行数据的函数，用于并发执行"""
    try:
        line = line.strip()
        if not line:
            return None, False

        data = json.loads(line)
        result = process_function(data, line_number, llm_name, llm_log_path, verbose)

        if result:
            with open(output_file_path, 'a', encoding='utf-8') as outfile:
                json.dump(result, outfile, ensure_ascii=False)
                outfile.write('\n')
                outfile.flush()
            return result, True
        return None, False

    except json.JSONDecodeError as e:
        if verbose:
            print(f"第 {line_number} 行JSON解析错误: {str(e)}")
        return None, False
    except Exception as e:
        if verbose:
            print(f"第 {line_number} 行处理错误: {str(e)}")
        return None, False

def process_jsonl_file(file_path, output_file_path, llm_log_path, process_func, llm_name="gpt-4",
                      max_workers=10, show_progress=True, verbose=True):
    """处理JSONL文件并生成两个输出文件，支持并发处理、进度条控制和打印控制"""
    try:
        # 初始化LLM日志文件和输出文件（清空）
        with open(llm_log_path, 'w', encoding='utf-8') as f:
            pass
        with open(output_file_path, 'w', encoding='utf-8') as f:
            pass

        total_lines = count_jsonl_lines(file_path)
        if verbose:
            print(f"开始处理文件，共 {total_lines} 行数据，使用模型: {llm_name}")
            print(f"并发数: {max_workers}")
            print(f"主输出文件: {output_file_path}")
            print(f"LLM调用日志: {llm_log_path}")

        success_count = 0
        error_count = 0
        start_time = time.time()

        # 读取所有行到内存中，以便并发处理
        lines = []
        with open(file_path, 'r', encoding='utf-8') as infile:
            for line in infile:
                lines.append(line.strip())

        # 使用线程池执行并发任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建所有待执行的任务
            futures = []
            for line_number, line in enumerate(lines, 1):
                if line:  # 跳过空行
                    future = executor.submit(
                        process_line,
                        line,
                        line_number,
                        llm_name,
                        llm_log_path,
                        output_file_path,
                        verbose
                    )
                    futures.append(future)

            # 监控任务完成进度
            if show_progress:
                pbar = tqdm(total=len(futures), desc="处理进度")
            else:
                pbar = None

            for future in as_completed(futures):
                result, success = future.result()
                if success:
                    success_count += 1
                else:
                    error_count += 1

                if pbar:
                    success_rate = (success_count / (success_count + error_count)) * 100 if (success_count + error_count) > 0 else 0
                    pbar.set_postfix({
                        "成功": success_count,
                        "失败": error_count,
                        "成功率": f"{success_rate:.2f}%"
                    })
                    pbar.update(1)

            if pbar:
                pbar.close()

        elapsed_time = time.time() - start_time
        if verbose:
            print(f"\n文件 {file_path} 处理完成")
            print(f"主输出已保存到 {output_file_path}")
            print(f"LLM日志已保存到 {llm_log_path}")
            print(f"处理统计: 总耗时 {elapsed_time:.2f} 秒，成功 {success_count} 行，失败 {error_count} 行，成功率 { (success_count/total_lines)*100:.2f}%")

    except FileNotFoundError:
        if verbose:
            print(f"错误: 文件 {file_path} 未找到")
    except Exception as e:
        if verbose:
            print(f"处理文件时发生错误: {str(e)}")

def process_function(data, line_number, llm_name, llm_log_path, verbose):
    """处理函数：区分qna和doc类型并调用LLM进行相关性判断"""
    if verbose:
        print(f"\n===== 处理第 {line_number} 行 =====")

    try:
        query = data['query']
        if verbose:
            display_query = query[:100] + "..." if len(query) > 100 else query
            print(f"\n【用户问题】: {display_query}\n")

        pos = []
        neg = []

        if 'value' in data:
            if verbose:
                print(f"value列表包含 {len(data['value'])} 个元素")

            for index, item in enumerate(data['value']):
                if verbose:
                    print(f"\n----- 处理第 {index+1} 个元素 -----")
                if isinstance(item, dict):
                    # Q&A类型
                    if 'qna_title' in item and 'qna_content' in item:
                        block = item['qna_content']
                        filename = item['qna_title']
                        source = filename

                        if verbose:
                            display_block = block[:100] + "..." if len(block) > 100 else block
                            print(f"【Q&A内容】: {display_block}")
                            print(f"【Q&A标题】: {filename}")
                            print(f"调用LLM ({llm_name}) 进行Q&A相关性判断...")

                        result = judge_relevance_with_llm(
                            query, block, source, llm_name, "qna",
                            line_number, index, llm_log_path, verbose
                        )

                        if verbose:
                            print(f"【判断结果】: {'相关' if result['is_relevant'] == 1 else '不相关' if result['is_relevant'] == 0 else '未知'}")
                            print(f"【判断原因】: {result['reason']}")

                        item_data = {
                            'content': item['qna_title'],
                            'filename': item.get('filename', ''),
                            'reason': result['reason'],
                            'from': 'qa'  # 来源标识
                        }

                        if result['is_relevant'] == 1:
                            pos.append(item_data)
                        elif result['is_relevant'] == 0:
                            neg.append(item_data)
                        else:
                            if verbose:
                                print(f"判定结果未知: {result['reason']}")

                    # 文档类型
                    elif 'document' in item and 'filename' in item:
                        block = item['document']
                        filename = item['filename']
                        source = filename

                        if verbose:
                            display_block = block[:100] + "..." if len(block) > 100 else block
                            print(f"【文档片段】: {display_block}")
                            print(f"【文档来源】: {filename}")
                            print(f"调用LLM ({llm_name}) 进行文档相关性判断...")

                        result = judge_relevance_with_llm(
                            query, block, source, llm_name, "doc",
                            line_number, index, llm_log_path, verbose
                        )

                        if verbose:
                            print(f"【判断结果】: {'相关' if result['is_relevant'] == 1 else '不相关' if result['is_relevant'] == 0 else '未知'}")
                            print(f"【判断原因】: {result['reason']}")

                        item_data = {
                            'content': block,
                            'filename': filename,
                            'reason': result['reason'],
                            'from': 'doc'  # 来源标识
                        }

                        if result['is_relevant'] == 1:
                            pos.append(item_data)
                        elif result['is_relevant'] == 0:
                            neg.append(item_data)
                        else:
                            if verbose:
                                print(f"判定结果未知: {result['reason']}")

                    else:
                        if verbose:
                            print(f"注意: 第 {index+1} 个元素不包含qna或doc所需的键")
                else:
                    if verbose:
                        print(f"第 {index+1} 个元素不是字典，无法获取键")

        return {
            'query': query,
            'pos': pos,
            'neg': neg
        }

    except KeyError as e:
        if verbose:
            print(f"错误: 数据中缺少必要的键 {e}")
        return None
    except Exception as e:
        if verbose:
            print(f"处理数据时发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(description='处理JSONL文件并使用LLM进行相关性判断的脚本')
    parser.add_argument('file_path', help='输入JSONL文件的路径')
    parser.add_argument('output_path', help='输出JSONL文件的路径（主输出）')
    parser.add_argument('--llm', choices=LLM_CONFIGS.keys(), default='gpt-4',
                      help=f'选择要使用的LLM模型，可选值: {list(LLM_CONFIGS.keys())}')
    parser.add_argument('--workers', type=int, default=20,
                      help='并发工作线程数，默认为10')
    parser.add_argument('--no-progress', action='store_true',
                      help='不显示进度条')
    parser.add_argument('--quiet', action='store_true',
                      help='安静模式，不打印详细信息（仅输出错误）')

    # 解析命令行参数
    args = parser.parse_args()

    # 生成LLM日志文件路径（复用主输出路径，修改后缀）
    base, ext = os.path.splitext(args.output_path)
    if not ext:
        llm_log_path = f"{base}_llm.log"
    else:
        llm_log_path = f"{base}_llm{ext}"

    # 处理文件，使用指定的参数
    process_jsonl_file(
        args.file_path,
        args.output_path,
        llm_log_path,
        process_function,
        args.llm,
        max_workers=args.workers,
        show_progress=not args.no_progress,
        verbose=not args.quiet
    )
