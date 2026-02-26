from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import json
import traceback  # 新增：导入堆栈追踪模块
from typing import List, Dict, Optional
import re
import sys

# 创建 FastAPI 应用实例
app = FastAPI(title="NL2SQL Server", version="1.1")


base = {
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
    "other": "其他属性"
}

tv = {
    "screenSizeInch": "屏幕尺寸(英寸)，例如80，110",
    "resolution": "分辨率, 该字段是字符串，例如2K、4K、5K、8K、FHD、HD、QHD、UHD、WQHD",
    "resolutionHorizontalPixels": "分辨率-横向像素，该字段是转化后的整数，例如：2160，4320 等；转化方式4k=2160",
    "refreshRate": "刷新频率，例如 160Hz， 120Hz",
    "refreshRateHz": "刷新频率(Hz)，该字段是去除Hz单位后的整数，例如 160， 120",
    "ramCapacity": "运存RAM，例如 4GB，8GB",
    "ramCapacityMb": "运存RAM(MB)，该字段是转为MB单位后的整数，例如 65536，4096",
    "romCapacity": "存储ROM，例如 64GB，128GB",
    "romCapacityMb": "存储ROM(MB)，该字段是转为MB单位后的整数，例如 65536，4096",
    "energyEfficiencyGrade": "能效等级，例如1级，2级，3级",
    "productWidthWithoutBaseMm": "不含底座产品尺寸(宽,mm)，例如 1230， 890",
    "productHeightWithoutBaseMm": "不含底座产品尺寸(高,mm)，例如 710， 520",
    "productThicknessWithoutBaseMm": "不含底座产品尺寸(厚,mm)，例如 80， 300",
    "productWidthWithBaseMm": "含底座产品尺寸(宽,mm)，例如 1250， 910",
    "productHeightWithBaseMm": "含底座产品尺寸(高,mm)，例如 730， 540",
    "productThicknessWithBaseMm": "含底座产品尺寸(厚,mm)，例如 200， 350"
}

air_conditioner = {
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
    "air_conditioner_horsepower": "空调匹数，例如1匹、2匹、3匹"
}

projector = {
    "screen_size_inch": "屏幕尺寸(英寸)，例如80，110",
    "resolution": "分辨率，该字段是字符串，例如2K、4K、5K、8K、FHD、HD、QHD、UHD、WQHD",
    "resolution_horizontal_pixels": "分辨率-横向像素，该字段是转化后的整数，例如：2160，4320 等；转化方式4k=2160",
    "refresh_rate": "刷新频率，例如 160Hz， 120Hz",
    "refresh_rate_hz": "刷新频率(Hz)，该字段是去除Hz单位后的整数，例如 160， 120",
    "ram_capacity": "运存RAM，例如 4GB，8GB",
    "ram_capacity_mb": "运存RAM(MB)，该字段是转为MB单位后的整数，例如 65536，4096",
    "rom_capacity": "存储ROM，例如 64GB，128GB",
    "rom_capacity_mb": "存储ROM(MB)，该字段是转为MB单位后的整数，例如 65536，4096",
    "energy_efficiency_rating": "能效等级，例如1级，2级，3级",
    "product_dimension_length_mm": "产品尺寸(长,mm)，例如 300， 450",
    "product_dimension_width_mm": "产品尺寸(宽,mm)，例如 200， 350",
    "product_dimension_height_mm": "产品尺寸(高,mm)，例如 100， 150"
}

monitor = {
    "screen_size_inch": "屏幕尺寸(英寸)，例如24，27，32",
    "resolution": "分辨率，该字段是字符串，例如2K、4K、5K、8K、FHD、HD、QHD、UHD、WQHD",
    "resolution_horizontal_pixels": "分辨率-横向像素，该字段是转化后的整数，例如：2160，4320 等；转化方式4k=2160",
    "software_system": "软件系统，包含：Android, Chrome OS, Google, Non OS, VIDAA U8, 其他, 无操作系统",
    "energy_efficiency_class": "能效等级，例如1级，2级，3级",
    "product_dimension_width_no_base_mm": "不含底座产品尺寸(宽,mm)，例如 600， 700",
    "product_dimension_height_no_base_mm": "不含底座产品尺寸(高,mm)，例如 400， 500",
    "product_dimension_width_with_base_mm": "含底座产品尺寸(宽,mm)，例如 620， 720",
    "product_dimension_height_with_base_mm": "含底座产品尺寸(高,mm)，例如 420， 520",
    "product_dimension_height2_with_base_mm": "含底座产品尺寸(高2,mm)【仅高低可调底座填写】，例如 450， 550",
    "product_weight_no_base_kg": "不含底座产品重量(kg)，例如 3.5， 5.0",
    "product_dimension_length_no_base_mm": "不含底座产品尺寸(长,mm)，例如 150， 200",
    "product_dimension_length_with_base_mm": "含底座产品尺寸(长,mm)，例如 170， 220"
}

refrigerator = {
"product_size_width_mm": "产品尺寸(宽,mm)，例如 600，700",
    "product_size_height_mm": "产品尺寸(高,mm)，例如 1800，2000",
    "product_size_depth_mm": "产品尺寸(深,mm)",
    "refrigerator_volume_l": "冷藏室容积(L)，例如 300，400",
    "freezer_volume_l": "冷冻室容积(L)，例如 100，200",
    "noise_dba": "噪音(dB(A))，例如 38，72",
    "comprehensive_power_consumption_kwh_per_24h": "综合耗电量(kW·h/24h)，例如 1.7，2.5"
}

cold_cabinet = {
    "energy_efficiency_class": "能效等级，例如1级，2级，3级",
    "product_size_width_mm": "产品尺寸(宽,mm)，例如 800，900",
    "product_size_height_mm": "产品尺寸(高,mm)，例如 850，950",
    "frequency_type": "变频/定频方式，例如 变频、定频",
    "product_size_depth_mm": "产品尺寸(深,mm)",
    "door_color": "门体颜色，例如冰釉白401号，凯撒银291号 等",
    "cabinet_color": "箱体颜色，例如钛空金FL49-1，冷灰色FL50-1 等",
    "noise_dba": "噪音(dB(A))，例如 40，60",
    "comprehensive_power_consumption_kwh_24h": "综合耗电量(kW·h/24h)，例如 1.2，2.0",
    "total_volume_l": "总容积(L)，例如 300，400",
    "temperature_zone": "温区，例如单温区、双温区、多温区"
}

washing_machine = {
    "energy_efficiency_rating": "能效等级，例如1级，2级，3级",
    "product_dimension_width_mm": "产品尺寸(宽,mm)，例如 600， 700",
    "product_dimension_height_mm": "产品尺寸(高,mm)，例如 850， 950",
    "key_press_method": "按键方式，例如 无、机械、触摸",
    "nominal_drying_capacity_kg": "标称烘干容量(kg)，例如 5，6",
    "nominal_dehydration_capacity_kg": "标称脱水容量(kg)，例如 7.5，8",
    "nominal_washing_capacity_kg": "标称洗涤容量(kg)，例如 8，9",
    "product_dimension_depth_mm": "产品尺寸(深,mm)",
    "motor_type": "电机类型，例如BLDC电机、DDM电机、DD电机、串激电机、感应电机",
    "rated_voltage_v": "额定电压(V)，例如 220， 230，240",
    "rated_frequency_hz": "额定频率(Hz)，例如60，50",
    "drying_method": "烘干方式，例如 冷凝、无、热泵、直排",
    "drainage_method": "排水方式，例如 上排水、下排水、水盒",
    "appearance_color": "外观颜色，例如珠光白、黑色、白色等",
    "washing_ratio": "洗净比，例如 1.2， 1.5",
    "display_type": "显示类型，例如 LED指示灯显示、内显、外显、None",
    "noise_dba": "噪音(dB(A))，例如 50，60",
    "refrigerant_type": "制冷剂种类，例如 R410A，R600a 等",
    "intelligent_dispensing": "智能投放，例如 单投、双投、无",
    "max_dehydration_speed_rpm": "最高脱水转速(rpm)，例如 1200，1400",
    "motor_fixed_or_inverter": "电机定变频，例如 定频、变频"
}

dryer = {
    "product_width_mm": "产品尺寸(宽,mm)，例如 600， 700",
    "product_height_mm": "产品尺寸(高,mm)，例如 850， 950",
    "nominal_drying_capacity_kg": "标称烘干容量(kg)，例如 5，6",
    "product_depth_mm": "产品尺寸(深,mm)",
    "motor_type": "电机类型，例如 BLDC电机、DDM电机、DD电机、串激电机、感应电机",
    "rated_voltage_v": "额定电压(V)，例如 220， 230，240",
    "rated_frequency_hz": "额定频率(Hz)，例如 60，50",
    "drying_method": "烘干方式，例如 分为：冷凝、无、热泵、直排",
    "appearance_color": "外观颜色，例如 珠光白，黑色，白色等",
    "noise_dba": "噪音(dB(A))，例如 50， 60"
}

chinese_to_english = {
    '电视': tv,
    '空调': air_conditioner,
    '投影': projector,
    '显示器': monitor,
    '冰箱' : refrigerator,
    '洗衣机': washing_machine,
    '烘干机': dryer,
    '冷柜': cold_cabinet,
}

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


def json_to_sql(json_data, table_name="products"):
    """
    将指定格式的JSON转换为SQL查询语句

    参数:
        json_data: 字典格式的查询条件（你的JSON解析后的数据）
        table_name: 要查询的数据库表名，默认是products
    返回:
        拼接好的SQL字符串
    """
    targets = json_data.get("targets", [])
    targets = [pro_to_col[item] for item in targets]
    if not targets:
        raise Exception(f"no targets")

    # 3. 处理WHERE子句
    where_conditions = []
    condition_list = json_data.get("condition", [])

    # 定义操作符映射（兼容JSON中的操作符名称）
    op_mapping = {
        "=": "=",
        ">": ">",
        "<": "<",
        ">=": ">=",
        "<=": "<=",
        "!=": "<>",
        "descending": "DESC",  # 排序用
        "ascending": "ASC",    # 排序用
        "like": "LIKE"
    }

    for cond in condition_list:
        prop_name = pro_to_col[cond.get("property_name")]
        targets.append(prop_name)
        prop_value = cond.get("property_value")
        prop_op = cond.get("property_op")
        if prop_name == 'model_name' or prop_name == 'sale_model_name' or prop_name == 'mid_class_name' or prop_name == 'on_sale_date':
            prop_op = 'like'
            prop_value = "%"+prop_value+"%"

        if prop_name == 'sale_brand_name':
            if prop_value =='海信':
                prop_value = 'Hisense'
        # 判断值类型：字符串加引号，数字不加
        if isinstance(prop_value, str) and not prop_value.isdigit():
            value_str = f"'{prop_value}'"
        else:
            value_str = prop_value

        # 拼接单个条件
        where_conditions.append(f"{prop_name} {op_mapping.get(prop_op, '=')} {value_str}")



    # 2. 处理FROM子句
    from_clause = f"FROM {table_name}"
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    # 4. 处理ORDER BY子句
    order_by_list = json_data.get("order_by", [])
    order_conditions = []
    for order in order_by_list:
        prop_name = pro_to_col[order.get("property_name")]
        targets.append(prop_name)
        order_op = order.get("order_op")
        order_conditions.append(f"{prop_name} {op_mapping.get(order_op, 'ASC')}")

    order_by_clause = "ORDER BY " + ", ".join(order_conditions) if order_conditions else ""

    # 5. 处理LIMIT子句
    count = json_data.get("count")
    if count is None or int(count)> 5 or int(count)==0:
        count =5
    limit_clause = f"LIMIT {count}"

    select_clause = f"SELECT {', '.join(targets)}"

    # 6. 拼接完整SQL
    sql_parts = [select_clause, from_clause, where_clause, order_by_clause, limit_clause]
    # 过滤空字符串，避免多余空格
    sql_parts = [part for part in sql_parts if part.strip()]
    sql = " ".join(sql_parts)

    return sql


class VLLMChatClient:
    """
    vLLM 聊天补全接口的 Python 客户端类
    用于调用本地部署的 vLLM 服务的 /v1/chat/completions 接口
    """

    def __init__(self, base_url: str = "http://localhost:8090", timeout: int = 30):
        """
        初始化客户端
        :param base_url: vLLM 服务的基础地址，默认是 http://localhost:8090
        :param timeout: 请求超时时间（秒），默认 30 秒
        """
        self.base_url = base_url.rstrip("/")  # 确保地址末尾没有斜杠
        self.chat_completions_url = f"{self.base_url}/v1/chat/completions"
        self.timeout = timeout
        self.session = requests.Session()  # 使用会话保持连接，提升性能

    def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        stream: bool = False
    ) -> Dict:
        """
        调用 vLLM 的聊天补全接口
        :param model: 模型名称，例如 "qwen3-32b-vllm"
        :param messages: 消息列表，包含 role 和 content 字段
        :param temperature: 生成温度，控制随机性，默认 0.7
        :param max_tokens: 最大生成令牌数，默认 512
        :param stream: 是否流式返回，默认 False
        :return: 接口返回的 JSON 响应字典
        """
        # 构造请求体
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        # 设置请求头
        headers = {
            "Content-Type": "application/json"
        }

        try:
            # 发送 POST 请求
            response = self.session.post(
                url=self.chat_completions_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout
            )
            # 检查响应状态码
            response.raise_for_status()
            # 返回 JSON 响应
            return response.json()

        except requests.exceptions.Timeout:
            raise Exception(f"请求超时（超时时间：{self.timeout} 秒）")
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接到 vLLM 服务：{self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP 错误：{e}，响应内容：{response.text}")
        except Exception as e:
            raise Exception(f"请求失败：{str(e)}")

    def close(self):
        """关闭会话连接"""
        self.session.close()


# 定义请求体的模型（用于数据校验）
class NL2SQLRequest(BaseModel):
    query: str
    struct_thred: Optional[float] = 0.5

# 定义默认的异常响应值
DEFAULT_ERROR_RESPONSE = {
    "code": 200,
    "results": {
        "is_struct": False,
        "struct_results": {},
        "sql": "",
        "subquery": "",
        "hit_filed": [],
        "struct_time": 0.0,
        "generate_sql_time": 0.0,
        "all_time": 0.0,
        "table_name": "",
        "env": "dev",
        "struct_desc":"请忽略我"
    },
    "message": "ok, let's go!!!!!!!"
}

# 定义模拟的响应数据（与你提供的示例保持一致）
BASE_MOCK_RESPONSE = {
    "code": 200,
    "results": {
        "is_struct": True,
        "struct_results": {
            "raw_model_output": "是",
            "yes_probability": 0.77729988964086
        },
        "sql": "",
        "subquery": "请忽略我啊",
        "hit_filed": [],
        "struct_time": 0.284,
        "generate_sql_time": 0.936,
        "all_time": 1.221,
        "table_name": "ads_mipd_aiplat_hiknow_product_insale_info_dd",
        "env": "dev",
        "struct_desc":""
    },
    "message": "success"
}

def has_no_chinese(text):
    pattern = r'^[^\u4e00-\u9fa5]*$'
    return re.match(pattern, text) is not None

# 定义 POST 接口，路径和参数与原接口保持一致
@app.post("/nl2sql")
async def nl2sql(
    user_key: str = Query(..., description="用户密钥参数"),  # ... 表示该参数为必填
    request_body: NL2SQLRequest = Body(...)  # 请求体，使用定义的模型校验
) -> Dict[str, Any]:
    """
    Mock NL2SQL 接口
    接收 POST 请求，返回固定的模拟响应数据
    """
    # 创建客户端实例（放在try外，避免创建失败也捕获）
    client = VLLMChatClient(base_url="http://localhost:8081", timeout=60)

    product = None
    query = request_body.query
    for key in chinese_to_english.keys():
        if key in query:
            product = chinese_to_english[key]
            break

    template_str = "\n".join([f"{k}: {v}" for k, v in base.items()])
    if product:
        product_str = "\n".join([f"{k}: {v}" for k, v in product.items()])
        template_str = "\n".join([template_str,product_str])

    #print(f'{query}\n{template_str}\n\n')

    try:
        # 构造请求消息
        prompt = f'''# 任务目标
解析用户输入的自然语言查询语句，精准识别其中的查询条件，并将条件映射到指定的属性字段列表中，输出结构化json，{{"condition":[{{"property_name":property_name,"property_value":property_value,"property_op":property_op}}],"targets":[target_property1,target_property2], "order_by":[{{"property_name":property_name, "order_op":order_op}}],"count": return count number}}用于后续生成SQL查询语句。
# 属性字段字典如下,没有对应属性填other,op不要包括between,非查询意图targets置空,严格按照用户query，不要多余字段
{template_str}
# 执行要求
请严格按照上述规则解析用户输入的query，输出符合格式要求的JSON数组，无需额外解释。
示例1:
用户query： 2025年发布的高端海信洗衣机的型号，价格从高到低
输出：{{"condition":[{{"property_name":actualSalesDate,"property_value":"2025","property_op":"="}},{{"property_name":"productMidCategoryName","property_value":"洗衣机","property_op":"="}},{{"property_name":"productPositionName","property_value":"高端","property_op":"="}}],"targets":["salesModelName"],"order_by":[{{"property_name":"salesPriceYuan", "order_op":"descending"}}]}}
用户输入如下：
{query}
'''
        print(f'{query}\n{prompt}\n\n')
        messages = [
            {"role": "user", "content": prompt}
        ]


        # 调用vLLM接口
        result = client.chat_completions(
            model="qwen4b",
            messages=messages,
            temperature=0,
            max_tokens=4096
        )

        result_content=result['choices'][0]['message']['content']
        pattern_optimized = r'[A-Za-z]+[A-Za-z0-9-]*[A-Za-z0-9]'
        optimized_extracted = re.findall(pattern_optimized, query)
        print(f'{query} extract: {optimized_extracted}')
        for item in optimized_extracted:
            if item not in result_content:
                print(f'{item} not in {result_content}')
                result_content=None
                break
        print(f'{request_body.query}:\n{result_content}')
        result_json = json.loads(result_content)

        #print(f'{request_body.query}:\n{result_content}')
        sql = json_to_sql(result_json, table_name="ads_mipd_aiplat_hiknow_product_insale_info_dd")





        # 更新模拟响应中的SQL
        MOCK_RESPONSE = BASE_MOCK_RESPONSE.copy()  # 深拷贝基础响应，避免修改原字典
        MOCK_RESPONSE["results"]['sql'] = sql
        MOCK_RESPONSE["results"]['struct_desc'] = ''
        print(f'{request_body.query}:\n{MOCK_RESPONSE}')

        return MOCK_RESPONSE

    except Exception as e:
        # 捕获所有异常，打印错误信息和完整堆栈
        error_msg = f"执行出错: {str(e)}"
        stack_trace = traceback.format_exc()  # 获取完整的堆栈信息
        print(f"\n{'='*50} 异常信息 {'='*50}")
        print(error_msg)
        print(f"\n{'='*50} 堆栈追踪 {'='*50}")
        print(stack_trace)
        print(f"{'='*100}\n")
        # 返回默认的错误响应
        return DEFAULT_ERROR_RESPONSE

    finally:
        # 无论是否发生异常，都关闭客户端连接
        client.close()

# 启动服务的入口
if __name__ == "__main__":
    import uvicorn
    # 启动服务，默认监听 8000 端口，允许外部访问（host="0.0.0.0"）
    uvicorn.run(app, host="0.0.0.0", port=8089)