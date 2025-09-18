import json
import argparse
import requests
import time
import random
from typing import Dict

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

def get_llm_prompt(query: str, block: str, source: str) -> str:
    """构建用于相关性判断的提示词"""
    return f"""你是一名信息检索与问答领域的专家。请你从多维度语义理解的角度，严格按照以下标准判断用户问题与检索到的文本块及其所在文件名之间的相关性：

相关性判定标准

- 检索内容结合文件名，能直接回答用户问题，或为问题提供明确的查询路径、操作方法、关键线索，判定为“相关”，结果为 1。
- 检索内容结合文件名，无法直接或间接回答问题，或仅为表层词汇相关、经验分享、泛泛描述、无事实/操作/政策支持，判定为“不相关”，结果为 0。
请综合考虑以下维度：

1. 直接/间接回答能力：检索内容能否直接回答问题，或间接提供查询路径、操作方法、关键线索。
2. 业务领域/场景归属：检索内容与问题是否属于同一业务领域或应用场景，信息粒度相符或略宽，能覆盖问题核心。
3. 信息粒度匹配：检索内容的信息细度是否与问题要求匹配。若粒度不完全匹配但能提供部分有效信息，可酌情判为相关。
4. 事实/数据/证据支持：检索内容是否为问题提供事实、数据、证据或有用线索，哪怕不能直接回答，也能为用户后续操作提供路径。
5. 排除表层词汇相关：仅词汇相关但实际内容无关的，判为不相关。
6. 排除经验/泛泛描述：仅为用户体验、主观评价、泛泛描述、无事实/操作/政策支持的内容，判为不相关。
7. 文件名辅助判断：文件名可辅助判断相关性，但不是唯一依据。
8. 排除无关流程/政策/其他产品信息：若检索内容为无关流程、政策、其他产品信息，判为不相关。
请你一步步思考，如果检索结果与用户问题在多个维度上相关，且能为问题提供直接答案或有用线索，则判定为“相关”；否则判定为“不相关”。请避免仅因部分词汇相关而判为相关。

典型示例归纳
- 保修/售后类：只要能覆盖产品、部件、期限等信息，判为相关。
- 故障/维修类：描述故障现象及处理建议，判为相关。
- 查询/操作类：提供查询方法或操作步骤，判为相关。
- 功能/模式类：说明功能原理或使用方法，判为相关。
- 经验/泛泛描述类：仅为主观体验，无事实/操作/政策支持，判为不相关。
参考示例（请严格参照示例理解相关性边界）：

示例1
- 问题：云视听小视频不能下载了怎么办？
- 检索内容：电视安装第三方应用软件，您可以参照以下安装步骤操作……【哈利提醒】：第三方软件未与系统适配，可能存在无法安装、安装后无法正常使用等情况……
- 判断：相关（因为内容提供了安装第三方软件的解决方法，能为用户问题提供参考和部分解决思路）
示例2
- 问题：55寸电视屏幕多少钱
- 检索内容：TCL 55Q10G Pro 液晶电视 55英寸 4K，￥4099。京东商城售价5999……（为整机价格）
- 判断：不相关（因为问题问的是“屏幕”价格，检索内容为整机价格，信息粒度不匹配，无法直接回答用户问题）
示例3
- 问题：临汾市尧都区容声冰箱售后电话
- 检索内容：容声客服热线：4008099999
- 判断：不相关（用户需要具体地区网点电话，检索内容为全国热线，信息范围不匹配）
示例4
- 问题：电视同一个配件坏，保修吗
- 检索内容：整机保修一年，主要部件保修三年……
- 判断：不相关（问题问的是配件维修后的保修政策，检索内容为整机/主要部件保修政策，信息粒度不匹配）
示例5
- 问题：2025年买的两个机器没有积分
- 检索内容：线上套购金额必须大于3999元，线下套购金额必须满8000元，才会有套购积分。
- 判断：不相关（检索内容为积分规则，无法判断用户机器是否为套购，业务逻辑不匹配，不能直接回答用户问题）
示例7
- 问题：冰箱冷冻室隔板坏了如何更换
- 检索内容：适用型号：BD/BC-280WFKJ/HX☆清理冷柜时，隔板盖层架的拆卸方式：1. 手部按住风道挡板下无层架区域，将层架部件从其凹槽拉出；2. 以底部支撑钢丝为旋转轴逆时针旋转一定角度使层架部件“弓”形支撑钢丝
- 判断：不相关（问的是冷冻室隔板，片段为隔板盖层架）
示例8
- 问题：信动力计划的薪资区间是什么？
- 检索内容：强调为能力付薪，提供完善的五险一金。入职后根据您的办公地提供免费公寓、免费班车、交通补贴、住房补贴、节日礼品、生日礼物等各种福利。具体待进入offer环节后，HR将会与您进行详细沟通。
- 判断：相关（薪资区间不是一个明确的值，上述片段能够支持回答该问题）
示例10
- 问题：电视设置睡眠功能的位置
- 检索内容：您可以按电视遥控器上的【设置】按键，进入电视设置；若没有设置按键，可以通过电视遥控器上的【智汇】或【菜单】按键进入设置。
- 判断：不相关（问的是电视设置睡眠功能在哪，片段是电视设置在哪）
示例11
- 问题：如何查询空调延保政策
- 检索内容：请您微信关注“海信爱家”点击右下角的“个人中心”选择“会员中心”点击进入后，下拉至最后，点击“电子保修卡”查看登记备案信息。
- 判断：相关（电子保修卡会包含保修相关信息）
示例12
- 问题：电视找不到账户与安全
- 检索内容：您好，您可以通过遥控上类似于齿轮图标按键进入电视设置，如没有找到，也可以通过遥控器【智汇】按键进入设置。
- 判断：相关（账户与安全也属于设置的范围）
示例13
- 问题：手机应用投屏怎么使用
- 检索内容：投屏不方便，操作复杂 只能一屏操作，不能多任务处理| 投屏/一屏双显示| 看手机APP影视/边看攻略边玩游戏/全家共 看手机照片/边看电视边健身-呼出“Hi投屏”按照步骤操作即可-
- 判断：不相关（并未说明怎么使用投屏）
示例14
- 问题：电视没有发票不能保修吗
- 检索内容：电视出现性能问题，凭正规发票或正规收据享受保修服务，整机保修一年，主要部件保修三年，特殊型号保修以实际政策为准。
- 判断：不相关（片段不能支撑问题的回答）
示例15：
- 问题：电视主板维修后，保修多久
- 片段：电视出现性能问题，凭正规发票或正规收据享受保修服务，整机保修一年，主要部件保修三年，特殊型号保修以实际政策为准。
- 判断：相关，电视及其配件的相关保修，都属于电视保修的范畴
示例16：
- 问题：空调像断电一样没反应了
- 片段：打开空调没反应，若是制热状态下，空调启动时，会有5-10分钟的预热过程，此时内机是不吹风的，防冷风功能，请耐心等待。其次制热过程中，需要停机化霜，此时内机会停，当化霜完毕后，内机会继续预热，然后正常工作，建议将温度设定高于室内温度5度左右
- 判断：相关
示例17：
- 问题：电视语音关不了机怎么办
- 片段：我的电视语音不能用了\n若您电视电视支持远场语音，请您按遥控器 设置 键，找到 AI 设置，进入 语音设置 ，打开可直接呼叫“海信小聚”，就可以找到哈利的朋友——小聚啦~若您打开后仍无法正常使用此功能，建议您进行热点测试，看能否正常使用远场语音，若可以正常使用，需要您咨询网络运营调试家中网络。若热点测试仍无法使用，建议您将电视 恢复出厂设置，恢复出厂后再次尝试能否正常使用此功能。【哈利提醒】：1.远场语音并非所有电视标配功能，若设置中无 语音设置 选项为不支持此功能。2.远场语音功能只可控制电视主页内容，无法控制第三方软件内容，如：银河奇异果、酷喵等。3.恢复出厂后电视恢复到最初系统，之前下载过的第三方软件或者账号都需重新下载或者登录。恢复出厂设置有一定的风险性，例如无法开机等现象，过程中请勿断电。
- 判断：相关，语音关不了机，可能是语音不能用导致的
示例18：
- 问题：冰箱主要部件保修三年是指什么
- 片段：冰箱整机包一年。主要部件包三年\n冰箱出现性能问题凭正规发票或正规收据享受保修服务，整机保修一年,主要部件保修三年，特殊型号保修以实际政策为准。
- 判断：相关，片段能够支撑问题的回答
示例19：
- 问题：电视机如何从壁挂取下来
- 片段：# 安装壁挂 1取出电视机，将电视机显示面朝下放置于水平桌面上，注意桌面上应铺垫柔软材料，避免划伤前壳表面。2先把后壳壁挂孔处2个把手上的螺钉拆除，再取下2个把手。3将电源线、HDMI延长线、天线隔离器、有线信号线延长线（根据实际需求选配）或自备有线信号线按实际需求接好，并放置于理线夹内，禁止线与线之间交叉重叠。注意理线后，线材不能外凸出后壳沉槽，以免影响壁挂安装。
- 判断：不相关，片段说的是怎么安装壁挂，问题是怎么从壁挂取下来
示例20：
- 问题：电视保修日期怎么查询
- 片段：电视如何查询保修期\n若电视出现性能问题，凭正规发票或正规收据享受保修服务，整机保修一年，主要部件保修三年，特殊型号保修以实际政策为准。
- 人工判断：相关
示例21：
- 问题：海信电视遥控器无法切换频道
- 片段：试着用语音功能查了下频道，基本能识别；遥控器支持语音，家里长辈偶尔会用；平常切换节目时会用到语音，感觉还挺方便；遥控器语音功能在设置菜单中能看到，可以按需使用；在看电视剧的时候用语音搜过演员的名字，还能识别出来；家人有时候用遥控说打开某个应用，都能正常执行；语音功能平常不常用，但也算一个可选项；遥控器带语音功能，实际体验感觉还可以；语音功能根本用不了，说什么都识别不出来；每次喊它都没反应，还得手动按遥控器；明明支持语音，结果经常提示无法识别；说了好几遍频道还是切换不了，很费劲；
- 判断：不相关，对于这类类似用户使用经验问题，均判断为不相关
示例21：
- 问题：电视噪音特别大,屏幕有圆点
- 片段：电视异响\n很抱歉给您带来不便，若电视有连接盒子等外接设备，请关掉外接设备后查看电视本身是否有异响。若关掉后正常，请检查外接设备。
- 判断：相关，噪声大，属于电视异响
示例22：
- 问题：容声158升立式冰柜主板坏
- 片段：冰柜退机\n正常情况下产品自销售之日起30天内，发生性能故障，消费者可以选择退、换产品，但是是否是性能故障还需要售后专业人员登门查看一下才能确定
- 人工判断：相关，首先容声属于冰柜冰箱，然后主板坏属于性能故障
示例23：
- 问题：海信电视支持3.2版本的U盘吗
- 片段：海信电视支持什么格式的u盘
请将U盘插到电脑上后，通过【我的电脑】找到U盘，单击右键，选择【格式化】，点击【文件系统】里有格式，选择FAT32或NTFS格式，温馨提示U盘内容一定提前备份好。
- 判断：相关，片段中不一定完全包含问题的答案，例如这个片段，包含具体支持什么格式，给到下游的大模型做回答时，如果没有问题的格式，则不支持，如果有，则支持，所以，这个片段与问题相关
示例24：
- 问题：洗衣机的除螨洗模式如何使用
- 片段：洗衣机的除螨洗模式
是水洗除螨程序，通过60℃持续30分钟深层渗透，消灭螨虫，再通过激荡水流实现强劲冲刷，带走螨虫残留。
- 判断：相关

输入：
用户问题（query）：{query}
检索文本块：{block}
文本块所在文件：{source}

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
        # 替换URL参数中的占位符
        formatted_params = {k: v.format(key=config["key"]) for k, v in url_params.items()}
        # 构建查询字符串
        query_string = "&".join([f"{k}={v}" for k, v in formatted_params.items()])
        # 拼接完整URL
        request_url = f"{config['url']}?{query_string}"
    else:
        request_url = config["url"]

    # 处理请求头，替换可能的占位符
    headers = {k: v.format(key=config["key"]) for k, v in config["headers"].items()}

    return request_url, headers

def parse_llm_response(response_text: str, query: str, block: str, source: str, llm_name: str) -> Dict[str, any]:
    """解析LLM返回的响应内容"""
    try:
        result = json.loads(response_text)

        # 验证返回格式是否正确
        if "is_relevant" in result and "reason" in result:
            # 确保is_relevant是整数0或1
            if result["is_relevant"] not in (0, 1):
                return {
                    "is_relevant": -1,
                    "reason": f"LLM返回的is_relevant值无效: {response_text}",
                    "query": query,
                    "block": block,
                    "source": source,
                    "llm_used": llm_name
                }
            # 添加原始输入信息和使用的模型
            result["query"] = query
            result["block"] = block
            result["source"] = source
            result["llm_used"] = llm_name
            return result
        else:
            return {
                "is_relevant": -1,
                "reason": f"LLM返回格式不正确: {response_text}",
                "query": query,
                "block": block,
                "source": source,
                "llm_used": llm_name
            }
    except json.JSONDecodeError:
        return {
            "is_relevant": -1,
            "reason": f"无法解析LLM返回的JSON: {response_text}",
            "query": query,
            "block": block,
            "source": source,
            "llm_used": llm_name
        }

def judge_relevance_with_llm(query: str, block: str, source: str, llm_name: str,
                           max_retries: int = 3, initial_delay: float = 1.0) -> Dict[str, any]:
    """
    使用指定的LLM判断用户问题与检索到的文本块及其来源的相关性，带有退火重试机制

    参数:
        query: 用户问题
        block: 检索到的文本块
        source: 文本块来源
        llm_name: 要使用的LLM模型名称
        max_retries: 最大重试次数
        initial_delay: 初始重试延迟时间(秒)

    返回:
        包含相关性判断结果的字典
    """
    try:
        # 构建提示词
        prompt = get_llm_prompt(query, block, source)

        # 创建请求payload
        payload = create_llm_request_payload(llm_name, prompt)

        # 准备请求参数
        request_url, headers = prepare_llm_request_parameters(llm_name)

        # 退火重试机制
        for attempt in range(max_retries + 1):
            try:
                # 调用LLM API
                response = requests.post(
                    request_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                # 解析响应
                if response.status_code == 200:
                    response_data = response.json()
                    llm_output = response_data["choices"][0]["message"]["content"].strip()
                    return parse_llm_response(llm_output, query, block, source, llm_name)
                else:
                    if attempt < max_retries:
                        reason = f"API请求失败 (状态码: {response.status_code})，将重试 (尝试 {attempt + 1}/{max_retries})"
                        print(f"{reason}: {response.text[:100]}...")
                    else:
                        return {
                            "is_relevant": -1,
                            "reason": f"API请求失败，状态码: {response.status_code}, 响应: {response.text}",
                            "query": query,
                            "block": block,
                            "source": source,
                            "llm_used": llm_name
                        }

            except Exception as e:
                if attempt < max_retries:
                    reason = f"调用LLM时发生错误，将重试 (尝试 {attempt + 1}/{max_retries})"
                    print(f"{reason}: {str(e)}")
                else:
                    return {
                        "is_relevant": -1,
                        "reason": f"调用LLM时发生错误: {str(e)}",
                        "query": query,
                        "block": block,
                        "source": source,
                        "llm_used": llm_name
                    }

            # 退火延迟
            if attempt < max_retries:
                delay = initial_delay * (2 **attempt) + random.uniform(0, 0.5 * initial_delay * (2** attempt))
                print(f"等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)

        return {
            "is_relevant": -1,
            "reason": "达到最大重试次数",
            "query": query,
            "block": block,
            "source": source,
            "llm_used": llm_name
        }

    except ValueError as e:
        return {
            "is_relevant": -1,
            "reason": str(e),
            "query": query,
            "block": block,
            "source": source,
            "llm_used": llm_name
        }

def process_jsonl_file(file_path, output_file_path, process_func, llm_name="gpt-4"):
    """
    读取JSONL文件并对每行进行处理，处理一行就即时写入一行到输出文件

    参数:
        file_path (str): 输入JSONL文件路径
        output_file_path (str): 输出JSONL文件路径
        process_func (function): 处理每行JSON数据的函数
        llm_name (str): 要使用的LLM模型名称
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as infile:
            line_number = 0
            for line in infile:
                line_number += 1
                try:
                    # 去除行首尾的空白字符
                    line = line.strip()
                    if not line:  # 跳过空行
                        continue

                    # 解析JSON
                    data = json.loads(line)

                    # 处理数据，传入llm_name参数
                    result = process_func(data, line_number, llm_name)

                    # 即时写入结果到输出文件
                    if result:
                        # 每次处理完一行就打开文件追加写入，然后关闭
                        with open(output_file_path, 'a', encoding='utf-8') as outfile:
                            json.dump(result, outfile, ensure_ascii=False)
                            outfile.write('\n')
                            outfile.flush()  # 强制刷新缓冲区，确保数据写入磁盘

                except json.JSONDecodeError as e:
                    print(f"第 {line_number} 行JSON解析错误: {str(e)}")
                except Exception as e:
                    print(f"第 {line_number} 行处理错误: {str(e)}")

        print(f"文件 {file_path} 处理完成，结果已保存到 {output_file_path}")

    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 未找到")
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")

def process_function(data, line_number, llm_name):
    """处理函数：区分qna和doc类型并调用LLM进行相关性判断，返回指定格式的结果"""
    print(f"\n处理第 {line_number} 行:")

    try:
        query = data['query']
        pos = []  # 存储相关的内容
        neg = []  # 存储不相关的内容

        # 处理value字段（假设它是一个列表）
        if 'value' in data:
            print(f"  value列表包含 {len(data['value'])} 个元素")

            # 遍历value列表中的每个item
            for index, item in enumerate(data['value']):
                # 检查item是否是字典类型
                if isinstance(item, dict):
                    # 判断是qna类型（包含qna_title和qna_content）
                    if 'qna_title' in item and 'qna_content' in item:
                        block = item['qna_content']
                        # 优先使用qna_title作为filename
                        filename = item['qna_title']
                        source = filename  # 对于qna类型，使用qna_title作为来源标识

                        # 调用LLM进行相关性判断
                        print(f"    调用LLM ({llm_name}) 进行相关性判断 (Q&A 项目 {index+1})...")
                        result = judge_relevance_with_llm(query, block, source, llm_name)

                        # 根据判断结果添加到pos或neg列表
                        item_data = {
                            'content': item['qna_title'],
                            'filename': item['filename']
                        }

                        if result['is_relevant'] == 1:
                            pos.append(item_data)
                            print(f"    判定为相关: {filename[:50]}...")
                        elif result['is_relevant'] == 0:
                            neg.append(item_data)
                            print(f"    判定为不相关: {filename[:50]}...")
                        else:
                            print(f"    判定结果未知: {result['reason']}")

                    # 判断是doc类型（包含document和filename）
                    elif 'document' in item and 'filename' in item:
                        block = item['document']
                        filename = item['filename']
                        source = filename

                        # 调用LLM进行相关性判断
                        print(f"    调用LLM ({llm_name}) 进行相关性判断 (文档项目 {index+1})...")
                        result = judge_relevance_with_llm(query, block, source, llm_name)

                        # 根据判断结果添加到pos或neg列表
                        item_data = {
                            'content': block,
                            'filename': filename
                        }

                        if result['is_relevant'] == 1:
                            pos.append(item_data)
                            print(f"    判定为相关: {filename[:50]}...")
                        elif result['is_relevant'] == 0:
                            neg.append(item_data)
                            print(f"    判定为不相关: {filename[:50]}...")
                        else:
                            print(f"    判定结果未知: {result['reason']}")

                    # 既不是qna也不是doc类型
                    else:
                        print(f"    注意: 第 {index+1} 个元素不包含qna或doc所需的键")
                else:
                    print(f"    第 {index+1} 个元素不是字典，无法获取键")

        # 构建返回结果
        result = {
            'query': query,
            'pos': pos,
            'neg': neg
        }

        return result

    except KeyError as e:
        print(f"  错误: 数据中缺少必要的键 {e}")
        return None
    except Exception as e:
        print(f"  处理数据时发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(description='处理JSONL文件并使用LLM进行相关性判断的脚本')
    parser.add_argument('file_path', help='输入JSONL文件的路径')
    parser.add_argument('output_path', help='输出JSONL文件的路径')
    parser.add_argument('--llm', choices=LLM_CONFIGS.keys(), default='gpt-4',
                      help=f'选择要使用的LLM模型，可选值: {list(LLM_CONFIGS.keys())}')

    # 解析命令行参数
    args = parser.parse_args()

    # 确保输出文件在开始处理前是清空的
    with open(args.output_path, 'w', encoding='utf-8') as f:
        pass  # 仅打开文件并立即关闭，清空文件内容

    # 使用参数化的文件路径和LLM模型调用处理函数
    process_jsonl_file(args.file_path, args.output_path, process_function, args.llm)
