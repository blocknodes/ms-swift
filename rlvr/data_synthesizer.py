import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional, Tuple, Union
import random
import time
import requests
import json
import time
import random
import requests
from typing import Dict, List, Optional
from typing import Callable, Dict, Any, Optional, List, Tuple
import os
from tqdm import tqdm



class SimpleLLMClient:
    """
    精简版LLM客户端，只保留自动重试功能
    """

    def __init__(self, llm_configs: Dict[str, Dict], default_llm: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            llm_configs: LLM模型配置字典
            default_llm: 默认使用的LLM模型名称
        """
        self.llm_configs = llm_configs
        self.default_llm = default_llm or next(iter(llm_configs.keys()))

        if self.default_llm not in self.llm_configs:
            raise ValueError(f"默认模型 {self.default_llm} 不在配置中")

    def _prepare_request_parameters(self, llm_name: str) -> tuple:
        """准备LLM API请求的URL和headers"""
        config = self.llm_configs[llm_name]

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

    def _create_payload(self, llm_name: str, messages: List[Dict[str, str]],
                       temperature: float = 0, n: int = 1, **kwargs) -> Dict:
        """创建LLM API请求的payload"""
        return {
            "model": self.llm_configs[llm_name]["model"],
            "messages": messages,
            "temperature": temperature,
            "n": n,
            **kwargs
        }

    def chat_completion(self, messages: List[Dict[str, str]], llm_name: Optional[str] = None,
                       temperature: float = 0, n: int = 1, max_retries: int = 3,
                       initial_delay: float = 1.0, **kwargs) -> Dict:
        """
        调用LLM的聊天接口，带自动重试功能

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}, ...]
            llm_name: LLM模型名称，不提供则使用默认模型
            temperature: 温度参数
            n: 返回结果数量
            max_retries: 最大重试次数
            initial_delay: 初始延迟时间（秒）
            **kwargs: 其他payload参数

        Returns:
            LLM返回的JSON响应
        """
        llm_name = llm_name or self.default_llm
        if llm_name not in self.llm_configs:
            raise ValueError(f"未知的LLM模型: {llm_name}")

        payload = self._create_payload(llm_name, messages, temperature, n, **kwargs)
        request_url, headers = self._prepare_request_parameters(llm_name)

        # 带指数退避的重试机制
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(request_url, json=payload, headers=headers, timeout=30)

                if response.status_code == 200:
                    return response.json()

                # 非200状态码，准备重试
                if attempt < max_retries:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                else:
                    return {"error": f"API请求失败，状态码: {response.status_code}", "details": response.text}

            except Exception as e:
                # 发生异常，准备重试
                if attempt < max_retries:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                else:
                    return {"error": "调用LLM时发生错误", "details": str(e)}

        return {"error": "达到最大重试次数"}






class MySQLClient:
    """
    MySQL 数据库客户端类，封装常用的数据库操作
    特性：
    - 自动管理连接（支持上下文管理器）
    - 支持事务操作
    - 完善的异常处理
    - 参数化查询（防止 SQL 注入）
    - 支持随机抽样指定字段
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "",
        charset: str = "utf8mb4"
    ):
        """
        初始化数据库连接参数
        :param host: MySQL 主机地址
        :param port: MySQL 端口
        :param user: 用户名
        :param password: 密码
        :param database: 要连接的数据库名
        :param charset: 字符集（utf8mb4 支持emoji等特殊字符）
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.connection: Optional[mysql.connector.connection.MySQLConnection] = None
        self.cursor: Optional[mysql.connector.cursor.MySQLCursorDict] = None

    def connect(self) -> None:
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset
            )
            # 使用 DictCursor，查询结果会以字典形式返回（更易读）
            self.cursor = self.connection.cursor(dictionary=True)
            print("数据库连接成功！")
        except Error as e:
            raise Exception(f"数据库连接失败: {e}")

    def close(self) -> None:
        """关闭数据库连接和游标"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("数据库连接已关闭")

    def query(self, sql: str, params: Tuple = ()) -> List[Dict]:
        """
        执行查询语句（SELECT）
        :param sql: 查询SQL语句（支持参数化，如 %s）
        :param params: SQL参数（元组形式，防止SQL注入）
        :return: 查询结果列表（每个元素是字典，key为字段名）
        """
        try:
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            return result
        except Error as e:
            raise Exception(f"查询失败: {e}")

    def execute(self, sql: str, params: Tuple = ()) -> int:
        """
        执行增删改语句（INSERT/UPDATE/DELETE）
        :param sql: 执行的SQL语句
        :param params: SQL参数
        :return: 受影响的行数
        """
        try:
            self.cursor.execute(sql, params)
            affected_rows = self.cursor.rowcount
            self.connection.commit()  # 自动提交
            return affected_rows
        except Error as e:
            self.connection.rollback()  # 失败回滚
            raise Exception(f"执行失败: {e}")

    def batch_execute(self, sql: str, params_list: List[Tuple]) -> int:
        """
        批量执行SQL语句（如批量插入）
        :param sql: 执行的SQL语句
        :param params_list: 参数列表（每个元素是一个参数元组）
        :return: 受影响的总行数
        """
        try:
            self.cursor.executemany(sql, params_list)
            affected_rows = self.cursor.rowcount
            self.connection.commit()
            return affected_rows
        except Error as e:
            self.connection.rollback()
            raise Exception(f"批量执行失败: {e}")

    def begin_transaction(self) -> None:
        """开启事务（关闭自动提交）"""
        self.connection.autocommit = False

    def commit_transaction(self) -> None:
        """提交事务"""
        try:
            self.connection.commit()
            print("事务提交成功")
        except Error as e:
            self.connection.rollback()
            raise Exception(f"事务提交失败: {e}")

    def rollback_transaction(self) -> None:
        """回滚事务"""
        self.connection.rollback()
        print("事务已回滚")

    # 上下文管理器支持（自动连接/关闭）
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"执行出错: {exc_val}")
            if self.connection:
                self.connection.rollback()
        self.close()

    def get_table_fields(self, table: str) -> List[str]:
        """
        获取指定表的所有字段名
        :param table: 表名
        :return: 字段名列表
        """
        try:
            # 查询表的字段信息
            self.cursor.execute(f"DESCRIBE {table}")
            # 提取字段名（DESCRIBE结果中第一列是Field）
            fields = [row["Field"] for row in self.cursor.fetchall()]
            return fields
        except Error as e:
            raise Exception(f"获取表字段失败: {e}")

    def sample_fields(
        self,
        table: str,
        fields: Union[str, List[str]] = "*",
        sample_size: int = 10,
        where_condition: str = "",
        where_params: Tuple = ()
    ) -> List[Dict]:
        """
        从指定表的特定字段中随机抽取样本数据
        :param table: 表名
        :param fields: 要抽样的字段，支持单个字段名、字段列表或 *（所有字段）
        :param sample_size: 抽样数量，默认10条
        :param where_condition: WHERE 条件语句（可选，如 "id > %s"）
        :param where_params: WHERE 条件对应的参数（防止SQL注入）
        :return: 随机抽样结果列表（每个元素是字典，key为字段名）
        """
        try:
            # 处理字段参数，转换为字符串形式
            if isinstance(fields, list):
                # 对字段名进行转义，防止SQL注入和关键字冲突
                field_str = ", ".join([f"`{field}`" for field in fields])
            elif fields == "*":
                field_str = "*"
            else:
                field_str = f"`{fields}`"

            # 构建基础SQL语句（使用 ORDER BY RAND() 实现随机抽样）
            sql = f"SELECT {field_str} FROM `{table}`"

            # 添加WHERE条件（如果有）
            if where_condition:
                sql += f" WHERE {where_condition}"

            # 添加随机排序和限制数量
            sql += f" ORDER BY RAND() LIMIT %s"

            # 组合参数（WHERE参数 + 抽样数量）
            params = where_params + (sample_size,)

            # 执行查询
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            return result

        except Error as e:
            raise Exception(f"随机抽样失败: {e}")

def write_to_jsonl(sample_data: Dict, file_path: str = "./samples.jsonl", append: bool = True):
    """
    将单个sample数据写入JSONL文件（每行一个JSON对象）

    Args:
        sample_data: 要写入的样本数据字典
        file_path: 输出文件路径
        append: 是否以追加模式写入（True=追加，False=覆盖）
    """
    # 确定文件打开模式：追加模式(a) 或 覆盖模式(w)
    mode = 'a' if append else 'w'
    # 确保文件目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        with open(file_path, mode, encoding='utf-8') as f:
            # 将字典转为JSON字符串并写入，每行一个
            json_line = json.dumps(sample_data, ensure_ascii=False)
            f.write(json_line + '\n')
    except Exception as e:
        print(f"写入JSONL文件失败: {e}")

# ------------------- 使用示例 -------------------
if __name__ == "__main__":
    # 配置数据库连接信息
    db_config = {
        "host": "10.19.37.217",
        "port": 9030,
        "user": "ds_hiknow_ro",
        "password": "dev_x5gN",  # 替换为你的密码
        "database": "ads"   # 替换为你的数据库名
    }


    # LLM配置
    LLM_CONFIGS = {
        "deepseek-v3": {
            "url": "https://aix-backup.hismarttv.com/v1/chat/completions",
            "headers": {"Content-Type": "application/json", "Authorization": "Bearer {key}"},
            "key": "x31ctKZ0ONfi1jkO",
            "model": "deepseek-v3",
            "url_params": {}
        },
        "gpt-4": {
            "url": "https://inner-apisix.hisense.com/openai/deployments/gpt-4-1/chat/completions",
            "headers": {"Content-Type": "application/json", "api-key": "Oi4rzFyLbMOmqVn8YYEyT2Pt0mkr3lgU"},
            "key": "nregzh6g2oviajyjstgzlhjsjmp9rtql",
            "model": "gpt-4-1",
            "url_params": {"user_key": "{key}"}
        },
        "qwen3-32b": {
            "url": "http://localhost:8088/v1/chat/completions",
            "headers": {"Content-Type": "application/json", "Authorization": "Bearer {key}"},
            "key": "x31ctKZ0ONfi1jkO",
            "model": "qwen3",
            "url_params": {}
        }
    }
    client = SimpleLLMClient(llm_configs=LLM_CONFIGS, default_llm="deepseek-v3")

    air_condioner = {
        "outerPackLengthMm": "外包装尺寸(长,mm)，例如 Decimal('1430')，Decimal('560')",
        "outerPackWidthMm": "外包装尺寸(宽,mm)，例如 Decimal('930')，Decimal('400')",
        "outerPackHeightMm": "外包装尺寸(高,mm)，例如 Decimal('200')，Decimal('780')",
        "grossWeightKg": "毛重(kg)，例如 Decimal('25')，Decimal('8.500')",
        "netWeightKg": "净重(kg)，例如 Decimal('22')，Decimal('7.500')",
        "colorName": "颜色名称，例如 亚瑟银H200号，星云灰340号 等",
        "productPositionName": "产品定位名称，例如 高端，中端，低端，1档，2档，3档等",
        "domesticExportSaleName": "内销/外销名称，例如 内销，外销",
        "productFamilyName": "产品家族名称，例如 M，U，Q等",
        "productSeriesName": "产品系列名称，例如 日立U享系列， 约克UD系列，XD3",
        "productModelName": "产品型号名称，例如 HKG-05DA/SG220XYBN#B，YUOH360VAEMCQ等",
        "salesModelName": "销售型号名称，例如 YVOH260VAEMBQ，YVOH800VAEMCQ等",
        "salesModelLifeCycleStatusName": "销售型号生命周期状态名称，例如 退市准备，开发，上市，立项，作废等",
        "salesAreaCode": "销售区域编码，例如 US，CN，AE 等",
        "salesAreaName": "销售区域名称，例如 中国，美国，德国 等",
        "promotionName": "推广名，例如 容声288S1，大薄荷E52Q等",
        "salesBrandName": "销售品牌名称，例如 Hisense，gorenje，KELON，Vidda，Ronshen等",
        "productBigCategoryName": "大类名称，例如 显示类产品，清洁卫生器具等",
        "productMidCategoryName": "中类名称，包含字符串：电视、投影、显示器、冰箱、冷柜、洗衣机、烘干机、空调、灶具、热水器",
        "productSmallCategoryName": "小类名称，例如平板电视、激光电视、波轮式洗衣机、滚筒式洗衣机等",
        "salesPriceYuan": "销售价格(元)",
        "actualSalesDate": "实际销售时间",
        "energy_efficiency_class": "能效等级，例如1级，2级，3级",
        "product_width_mm": "产品尺寸(宽,mm)，例如 800，900",
        "product_height_mm": "产品尺寸(高,mm)，例如 300，400",
        "frequency_type": "变频/定频，例如 变频， 定频",
        "product_depth_mm": "产品尺寸(深,mm)",
        "main_body_color": "外观主体颜色，例如紫砂咖，烟紫金，莫奈金等",
        "indoor_unit_model": "内机产品型号，例如KFR-72L/QZ1-X1A(2X03)，KFR-35GW/EFVAA1+1U35E3A等",
        "outdoor_unit_model": "外机产品型号，例如KFR-35W/H3V7X1(1X41)，KFR-72LW/H3V7X1(2X41)等",
        "noise_dba": "噪音(dB(A))，例如 45， 55",
        "air_conditioner_type": "空调柜机或挂机，例如柜机、挂机",
        "air_conditioner_horsepower": "空调匹数，例如1匹、2匹、3匹"}

    pro_to_col = {
        "outerPackLengthMm": "product_long",
        "outerPackWidthMm": "product_wide",
        "outerPackHeightMm": "product_high",
        "grossWeightKg": "gross_weight",
        "netWeightKg": "net_weight",
        "colorName": "color_name",
        "productPositionName": "product_pnt_name",
        "domesticExportSaleName": "inout_sale_name",
        "productFamilyName": "family_name",
        "productSeriesName": "series_name",
        "productModelName": "model_name",
        "salesModelName": "sale_model_name",
        "salesModelLifeCycleStatusName": "sale_model_lca_name",
        "salesAreaCode": "sale_area_code",
        "salesAreaName": "sale_area_name",
        "promotionName": "promotion_name",
        "salesBrandName": "sale_brand_name",
        "productBigCategoryName": "big_class_name",
        "productMidCategoryName": "mid_class_name",
        "productSmallCategoryName": "small_class_name",
        "salesPriceYuan": "retail_h",
        "actualSalesDate": "on_sale_date",
        #### TV
        "screenSizeInch": "PC00003",
        "resolution": "PC00005",
        "resolutionHorizontalPixels": "PC00005_CL",
        "refreshRate": "PC00007",
        "refreshRateHz": "PC00007_CL",
        "ramCapacity": "PC00009",
        "ramCapacityMb": "PC00009_CL",
        "romCapacity": "PC00010",
        "romCapacityMb": "PC00010_CL",
        "energyEfficiencyGrade": "PC00024",
        "productWidthWithoutBaseMm": "PC00042",
        "productHeightWithoutBaseMm": "PC00043",
        "productThicknessWithoutBaseMm": "PC00044",
        "productWidthWithBaseMm": "PC00045",
        "productHeightWithBaseMm": "PC00046",
        "productThicknessWithBaseMm": "PC00047",
        ### air conditioner
        "energy_efficiency_class": "PC00024",
        "product_width_mm": "PC00080",
        "product_height_mm": "PC00081",
        "frequency_type": "PC10003",
        "product_depth_mm": "PC10008",
        "main_body_color": "PC20083",
        "indoor_unit_model": "PC20029",
        "outdoor_unit_model": "PC20055",
        "noise_dba": "PC10093",
        "air_conditioner_type": "product_spec",
        "air_conditioner_horsepower": "spec_range",
        ### projector
        "screen_size_inch": "PC00003",
        "resolution": "PC00005",
        "resolution_horizontal_pixels": "PC00005_CL",
        "refresh_rate": "PC00007",
        "refresh_rate_hz": "PC00007_CL",
        "ram_capacity": "PC00009",
        "ram_capacity_mb": "PC00009_CL",
        "rom_capacity": "PC00010",
        "rom_capacity_mb": "PC00010_CL",
        "energy_efficiency_rating": "PC00024",
        "product_dimension_length_mm": "PC00079",
        "product_dimension_width_mm": "PC00080",
        "product_dimension_height_mm": "PC00081",
        ### monitor
        "screen_size_inch": "PC00003",
        "resolution": "PC00005",
        "resolution_horizontal_pixels": "PC00005_CL",
        "software_system": "PC00011",
        "energy_efficiency_class": "PC00024",
        "product_dimension_width_no_base_mm": "PC00042",
        "product_dimension_height_no_base_mm": "PC00043",
        "product_dimension_width_with_base_mm": "PC00045",
        "product_dimension_height_with_base_mm": "PC00046",
        "product_dimension_height2_with_base_mm": "PC00048",
        "product_weight_no_base_kg": "PC00049",
        "product_dimension_length_no_base_mm": "PC00095",
        "product_dimension_length_with_base_mm": "PC00179",
        ### refrigerator
        "product_size_width_mm": "PC00080",
        "product_size_height_mm": "PC00081",
        "product_size_depth_mm": "PC10008",
        "refrigerator_volume_l": "PC10047",
        "freezer_volume_l": "PC10048",
        "noise_dba": "PC10093",
        "comprehensive_power_consumption_kwh_per_24h": "PC10106",
        ### cold cabit
        "energy_efficiency_class": "PC00024",
        "product_size_width_mm": "PC00080",
        "product_size_height_mm": "PC00081",
        "frequency_type": "PC10003",
        "product_size_depth_mm": "PC10008",
        "door_color": "PC10054",
        "cabinet_color": "PC10086",
        "noise_dba": "PC10093",
        "comprehensive_power_consumption_kwh_24h": "PC10106",
        "total_volume_l": "PC10107",
        "temperature_zone": "PC10120",
        ## washing machine
        "energy_efficiency_rating": "PC00024",
        "product_dimension_width_mm": "PC00080",
        "product_dimension_height_mm": "PC00081",
        "key_press_method": "PC10001",
        "nominal_drying_capacity_kg": "PC10004",
        "nominal_dehydration_capacity_kg": "PC10005",
        "nominal_washing_capacity_kg": "PC10006",
        "product_dimension_depth_mm": "PC10008",
        "motor_type": "PC10022",
        "rated_voltage_v": "PC10025",
        "rated_frequency_hz": "PC10027",
        "drying_method": "PC10036",
        "drainage_method": "PC10060",
        "appearance_color": "PC10074",
        "washing_ratio": "PC10078",
        "display_type": "PC10081",
        "noise_dba": "PC10093",
        "refrigerant_type": "PC10097",
        "intelligent_dispensing": "PC10101",
        "max_dehydration_speed_rpm": "PC10109",
        "motor_fixed_or_inverter": "PC10113",
        ## dryer
        "product_width_mm": "PC00080",
        "product_height_mm": "PC00081",
        "nominal_drying_capacity_kg": "PC10004",
        "product_depth_mm": "PC10008",
        "motor_type": "PC10022",
        "rated_voltage_v": "PC10025",
        "rated_frequency_hz": "PC10027",
        "drying_method": "PC10036",
        "appearance_color": "PC10074",
        "noise_dba": "PC10093"
    }


    air_condioner_db_values={}
    #fields 从 db中真实取得
    with MySQLClient(**db_config) as db:
        table = 'ads_mipd_aiplat_hiknow_product_insale_info_dd'

        # 1. 获取表的所有字段
        all_fields = db.get_table_fields(table)
        print("表的所有字段:", all_fields)

        for key in air_condioner.keys():

            sql = f"SELECT DISTINCT {pro_to_col[key]} FROM {table} WHERE mid_class_name like CONCAT('%', '空调', '%')"

            result = db.query(sql)
            air_condioner_db_values[key]=[]
            for item in result:
                for k, v in item.items():
                    #print(str(v))
                    if str(v) == 'None':
                        #raise
                        print(str(v))
                        continue
                    air_condioner_db_values[key].append(str(v))
            #print("\n\n查询结果:", result)
            #import pdb;pdb.set_trace()
            if len(air_condioner_db_values[key])==0:
                del air_condioner_db_values[key]
    print(air_condioner_db_values)




    for i in tqdm(range(10000), desc="执行循环", unit="次"):
        random_models = random.sample(air_condioner_db_values["salesModelName"], k=3)
        random_models='，'.join(random_models)


        prompt = f"""任务描述： 你是一个数据合成专家：以下是数据的schema。
schema：
    "salesModelName": "销售型号名称，例如{random_models}等",
    "salesBrandName": "销售品牌名称，例如 Hisense，gorenje，KELON，Vidda，Ronshen等",
    "salesPriceYuan": "销售价格(元)",
    "actualSalesDate": "实际销售时间，如：2025-12-16，2023-01-04等",
    "energy_efficiency_class": "能效等级，例如1级，2级，3级",

    "frequency_type": "变频/定频，例如 变频， 定频",
    "air_conditioner_type": "空调柜机或挂机，例如柜机、挂机",
    "air_conditioner_horsepower": "空调匹数，例如1匹、2匹、3匹"
json字段说明：
targets：询问的目标属性，必选字段
conditions: 过滤的条件，可选字段



根据以上schema,合成对应的问题，问题要全面反映target 和condition，问题中要包含空调两个字.
示例1:
{{"query":"KL-500B3C6/F空调的颜色是什么","targets":["productModelName"],"conditions":[{{"property_name":"salesModelName","property_value":"KL-500B3C6/F","op":"="}}]}}

请输出一条json
"""
    # 发送请求
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(
            messages=messages,
            temperature=0.8,
            max_retries=20,
            n=1
        )


        print(f'{prompt}:\n{response["choices"][0]["message"]["content"]}')
        for item in response['choices']:
            result = item['message']['content']
            if result.startswith('```json'):
                result=result.split('```json')[1].split('```')[0]
            result = json.loads(result)

            output ={'instruction':'','input':result['query'], 'output': json.dumps(result,ensure_ascii=False)}

            #print(output)
            write_to_jsonl(output)

    #     db.close()