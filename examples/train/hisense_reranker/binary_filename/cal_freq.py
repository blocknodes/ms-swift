import jieba
from collections import Counter
import os
import sys

def chinese_word_frequency_from_file(
    file_path,
    stopwords_path=None,
    top_n=20,
    encoding='utf-8'
):
    """
    读取中文文本文件，使用jieba分词统计词频
    :param file_path: 待分析的文本文件路径（.txt格式）
    :param stopwords_path: 停用词文件路径（可选）
    :param top_n: 显示词频前N的词汇，默认20
    :param encoding: 文件编码格式，默认utf-8（常见还有gbk）
    :return: 词频统计结果（字典）
    """
    # 1. 验证文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"错误：未找到文件 {file_path}")

    # 2. 读取文件内容
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            text = f.read()  # 读取整个文件内容
        print(f"成功读取文件：{file_path}")
        print(f"文件总字符数：{len(text)}\n")
    except Exception as e:
        raise Exception(f"读取文件失败：{str(e)}")

    # 3. 定义默认停用词
    default_stopwords = {
        '的', '了', '是', '在', '和', '有', '我', '你', '他', '她', '它',
        '我们', '你们', '他们', '这', '那', '个', '件', '条', '只', '本',
        '就', '都', '也', '还', '很', '非常', '比较', '太', '不', '没',
        '要', '会', '能', '可以', '应该', '可能', '因为', '所以', '如果',
        '虽然', '但是', '而且', '或者', '这里', '那里', '什么', '怎么',
        '哪里', '多少', '一些', '一点', '所有', '任何', '每一个', '各自'
    }

    # 4. 加载自定义停用词（如果提供）
    if stopwords_path:
        if os.path.exists(stopwords_path):
            with open(stopwords_path, 'r', encoding=encoding) as f:
                custom_stopwords = set(f.read().splitlines())
            stopwords = default_stopwords.union(custom_stopwords)
            print(f"成功加载停用词文件：{stopwords_path}")
        else:
            print(f"警告：未找到停用词文件 {stopwords_path}，使用默认停用词")
            stopwords = default_stopwords
    else:
        stopwords = default_stopwords

    # 5. jieba分词（精确模式）
    words = jieba.lcut(text)  # 返回列表格式，便于过滤

    # 6. 过滤规则：去除停用词、单字、空字符串
    filtered_words = [
        word for word in words
        if len(word) >= 2  # 过滤单字
        and word not in stopwords  # 过滤停用词
        and word.strip()  # 过滤空字符串（如换行符、空格）
    ]

    # 7. 统计词频
    word_freq = Counter(filtered_words)

    # 8. 输出结果
    print(f"分词后有效词汇总数：{len(filtered_words)}")
    print(f"\n词频前{top_n}名：")
    for rank, (word, freq) in enumerate(word_freq.most_common(top_n), 1):
        print(f"{rank:2d}. {word:<10} → {freq}次")

    return dict(word_freq)

# ------------------- 示例使用 -------------------
if __name__ == "__main__":
    # 配置参数（根据你的文件路径修改！）
    CONFIG = {
        "file_path": sys.argv[1],  # 待分析的文本文件（必填）
        "stopwords_path": "stopwords.txt",  # 自定义停用词文件（可选）
        "top_n": 30,  # 显示前15个高频词
        "encoding": "utf-8"  # 文件编码（如果是Windows记事本保存的文件，可能需要改为"gbk"）
    }

    try:
        # 调用函数进行文件处理和词频统计
        result = chinese_word_frequency_from_file(**CONFIG)

        # 可选：将结果保存到文件（如需要）
        save_result = input("\n是否将词频结果保存到文件？(y/n)：").strip().lower()
        if save_result == 'y':
            with open("词频统计结果.txt", 'w', encoding='utf-8') as f:
                f.write("词频统计结果\n")
                f.write("-" * 30 + "\n")
                for word, freq in sorted(result.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{word:<10} → {freq}次\n")
            print("结果已保存到：词频统计结果.txt")

    except Exception as e:
        print(f"程序执行失败：{str(e)}")