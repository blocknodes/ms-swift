import subprocess
import json
import shlex
from typing import Dict, Any, Optional

def execute_command(command: str) -> Dict[str, Any]:
    """
    执行单个命令并返回包含结果的字典

    Args:
        command: 要执行的命令字符串

    Returns:
        包含命令、返回码、输出和错误信息的字典
    """

    # 使用shlex.split处理命令，支持带空格的参数
    args = shlex.split(command)

    # 执行命令，捕获 stdout 和 stderr
    result = subprocess.run(
        args,
        check=False,  # 不抛出异常，我们自己处理返回码
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True  # 直接返回字符串而不是字节
    )

    # 解析stdout（如果是JSON格式）
    parsed_stdout = parse_stdout(result.stdout)
    #assert len(parsed_stdout['records']['splitQueryList']) == 1
    query = parsed_stdout['records']['splitQueryList'][0]

    qnas = parsed_stdout['records']['qnaRunResult']['qnaAfterRerankResult']
    #import pdb;pdb.set_trace()

    finals = parsed_stdout['records']['finalRecallResult']
    finals = [{'kind':item['metadata']['kind'],'filename':item['file_name'],'title': item['title'], 'content':item['content'],
        'score':item['score'], 'llm_relervance': 0} for item in finals]

    # 按score从高到低排序（原地排序）
    finals.sort(key=lambda x: x['score'], reverse=True)

    # 返回包含命令执行信息的字典
    return {
        "query": query,
        #"qna": qnas,
        #"doc": docs,
        "finals": finals[:],


    }


def parse_stdout(stdout: str) -> Optional[Dict[str, Any]]:
    """
    尝试解析stdout为JSON格式

    Args:
        stdout: 命令输出的stdout字符串

    Returns:
        解析后的字典，如果解析失败则返回None
    """
    try:
        if stdout.strip():  # 仅当stdout不为空时尝试解析
            return json.loads(stdout)
        return None
    except json.JSONDecodeError:
        # 如果不是JSON格式，返回None
        return None

def process_commands_file(input_path: str, output_path: str) -> None:
    """
    处理命令文件，支持多行命令（以反斜杠结尾）和空行分隔命令，
    执行所有命令并将结果写入JSONL文件

    Args:
        input_path: 包含命令的输入文件路径
        output_path: 输出JSONL文件路径
    """

    # 读取输入文件中的所有命令，支持多行命令和空行分隔
    commands = []
    current_command = []

    with open(input_path, 'r') as f:
        for line in f:
            # 去除行首尾的空白字符
            stripped_line = line.strip()

            # 如果是空行且当前有正在构建的命令，则表示一个命令结束
            if not stripped_line:
                if current_command:
                    # 合并当前命令的所有行，去除反斜杠
                    full_command = ' '.join([part.rstrip('\\') for part in current_command])
                    commands.append(full_command)
                    current_command = []
                continue  # 跳过空行

            # 将行添加到当前命令
            current_command.append(stripped_line)

            # 如果行不以反斜杠结尾，说明当前命令结束（但可能后面还有内容）
            if not stripped_line.endswith('\\'):
                # 不立即添加，等待空行或下一个命令的开始
                pass

    # 检查文件结束时是否还有未完成的命令
    if current_command:
        full_command = ' '.join([part.rstrip('\\') for part in current_command])
        commands.append(full_command)

    # 执行命令并写入结果到JSONL文件
    with open(output_path, 'w') as f:
        for i, command in enumerate(commands, 1):
            print(f"执行命令 {i}/{len(commands)}: {command}")
            result = execute_command(command)
            # 写入JSON行
            json.dump(result, f, ensure_ascii=False)
            f.write('\n')  # 每条记录占一行

            # 示例：如果解析成功，可以在这里处理解析后的结果
            if result.get('parsed_stdout'):
                print(f"  解析成功，找到 {len(result['parsed_stdout'].get('records', []))} 条记录")

    print(f"所有命令处理完成，结果已写入 {output_path}")



if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) != 3:
        print("用法: python command_processor.py <输入命令文件> <输出JSONL文件>")
        print("示例: python command_processor.py commands.txt results.jsonl")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # 处理命令文件
    process_commands_file(input_file, output_file)
