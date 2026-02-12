"""Translate Chinese text in car data to English."""

import json
import sys
from pathlib import Path

# Translation dictionary for common Chinese terms
TRANSLATIONS = {
    # Common car terms
    "胎压监测装置": "Tire Pressure Monitoring System",
    "主动刹车/主动安全系统": "Active Braking/Active Safety System",
    "ISOFIX儿童座椅接口": "ISOFIX Child Seat Interface",
    "自动驻车": "Auto Hold",
    "方向盘换挡": "Steering Wheel Shift",
    "蓝牙/车载电话": "Bluetooth/Car Phone",
    "车内PM2.5过滤装置": "In-Car PM2.5 Filter",
    "后排出风口": "Rear Air Outlet",
    "自动泊车入位": "Auto Parking",
    "无钥匙启动系统": "Keyless Start System",
    "主动闭合式进气格栅": "Active Grille Shutters",
    
    # Configuration groups
    "基本参数": "Basic Parameters",
    "车身": "Body",
    "发动机": "Engine",
    "变速箱": "Transmission",
    "底盘转向": "Chassis & Steering",
    "车轮制动": "Wheels & Brakes",
    
    # Configuration parameters
    "车型名称": "Model Name",
    "厂商指导价(元)": "Manufacturer Suggested Retail Price (CNY)",
    "厂商": "Manufacturer",
    "级别": "Class",
    "能源类型": "Energy Type",
    "环保标准": "Emission Standard",
    "上市时间": "Launch Date",
    "最大功率(kW)": "Max Power (kW)",
    "最大扭矩(N·m)": "Max Torque (N·m)",
    "发动机": "Engine",
    "变速箱": "Transmission",
    "长*宽*高(mm)": "Length*Width*Height (mm)",
    "车身结构": "Body Structure",
    "最高车速(km/h)": "Max Speed (km/h)",
    "官方0-100km/h加速(s)": "Official 0-100km/h Acceleration (s)",
    "NEDC综合油耗(L/100km)": "NEDC Combined Fuel Consumption (L/100km)",
    "整车质保": "Vehicle Warranty",
    "首任车主质保政策": "First Owner Warranty Policy",
    "长度(mm)": "Length (mm)",
    "宽度(mm)": "Width (mm)",
    "高度(mm)": "Height (mm)",
    "轴距(mm)": "Wheelbase (mm)",
    "前轮距(mm)": "Front Track (mm)",
    "后轮距(mm)": "Rear Track (mm)",
    "车门数(个)": "Number of Doors",
    "座位数(个)": "Number of Seats",
    "油箱容积(L)": "Fuel Tank Capacity (L)",
    "后备厢容积(L)": "Trunk Volume (L)",
    "整备质量(kg)": "Curb Weight (kg)",
    "发动机型号": "Engine Model",
    "排量(mL)": "Displacement (mL)",
    "排量(L)": "Displacement (L)",
    "进气形式": "Intake Type",
    "发动机布局": "Engine Layout",
    "气缸排列形式": "Cylinder Arrangement",
    "气缸数(个)": "Number of Cylinders",
    "每缸气门数(个)": "Valves per Cylinder",
    "配气机构": "Valve Train",
    "最大马力(Ps)": "Max Horsepower (Ps)",
    "最大功率转速(rpm)": "Max Power RPM",
    "最大扭矩转速(rpm)": "Max Torque RPM",
    "最大净功率(kW)": "Max Net Power (kW)",
    "燃料形式": "Fuel Type",
    "燃油标号": "Fuel Grade",
    "供油方式": "Fuel Supply",
    "缸盖材料": "Cylinder Head Material",
    "缸体材料": "Cylinder Block Material",
    "挡位个数": "Number of Gears",
    "变速箱类型": "Transmission Type",
    "简称": "Abbreviation",
    "驱动方式": "Drive Type",
    "四驱形式": "4WD Type",
    "中央差速器结构": "Center Differential Structure",
    "前悬架类型": "Front Suspension Type",
    "后悬架类型": "Rear Suspension Type",
    "助力类型": "Power Steering Type",
    "车体结构": "Body Structure",
    "前制动器类型": "Front Brake Type",
    "后制动器类型": "Rear Brake Type",
    "驻车制动类型": "Parking Brake Type",
    "前轮胎规格": "Front Tire Specification",
    "后轮胎规格": "Rear Tire Specification",
    "备胎规格": "Spare Tire Specification",
    
    # Extra section
    "内部配置": "Interior Configuration",
    "多媒体配置": "Multimedia Configuration",
    "空调配置": "Air Conditioning Configuration",
    "安全配置": "Safety Configuration",
    "辅助/操控配置": "Assist/Control Configuration",
    "外部/防盗配置": "External/Anti-theft Configuration",
    
    # Inspection
    "维修保养查询": "Maintenance Query",
    "记录全透明，拒绝事故车": "Fully Transparent Records, Reject Accident Vehicles",
    "记录查询": "Record Query",
    
    # Map tags
    "过户次数": "Transfer Count",
    "里程": "Mileage",
    "车龄": "Vehicle Age",
    "三年保值率": "3-Year Resale Value",
    "很少": "Very Few",
    "少": "Few",
    "低": "Low",
    "一般": "Average",
    "长": "Long",
    
    # Loan
    "分期购车": "Installment Purchase",
    "超低首付开回家": "Ultra Low Down Payment Drive Home",
    "期": "Period",
    
    # Fault
    "车况排查报告查询": "Vehicle Condition Check Report Query",
    "碰撞时间、修复金额、修复明细": "Collision Time, Repair Amount, Repair Details",
    
    # Rank
    "本地同级销量榜第1名": "Local Same-Class Sales Rank #1",
    "本地同级保值榜第6名": "Local Same-Class Resale Value Rank #6",
    
    # Price analysis
    "符合相似车源均价": "Matches Average Price of Similar Vehicles",
    "价格实惠抢手  浏览人数较多": "Affordable Price, Popular, Many Viewers",
    
    # Cost performance
    "本车保值率较高，预计未来三年内价格相对平稳。": "This vehicle has a high resale value, expected to remain relatively stable in the next three years.",
    "该车过户次数为0次，属于一手好车,保值率较高，预计未来三年内价格相对平稳": "This vehicle has 0 transfers, is a first-hand good car with high resale value, expected to remain relatively stable in the next three years",
    
    # Business
    "以旧换新": "Trade-in",
    "用旧车置换 省钱又省心": "Trade in old car, save money and worry",
    "首付4.08万 轻松开回家": "Down payment 40,800, drive home easily",
    "查月供": "Check Monthly Payment",
    "事故排查": "Accident Check",
    "快速规避事故车": "Quickly Avoid Accident Vehicles",
    "该车可迁入 中山": "This vehicle can be registered in Zhongshan",
    "寄存于中山仓": "Stored in Zhongshan Warehouse",
    "3成首付4.08万起，超值购车": "30% down payment from 40,800, great value purchase",
    
    # Common values
    "汽油": "Gasoline",
    "汽油+48V轻混系统": "Gasoline + 48V Mild Hybrid System",
    "涡轮增压": "Turbocharged",
    "三厢车": "Sedan",
    "中型车": "Midsize Car",
    "紧凑型车": "Compact Car",
    "大型车": "Full-size Car",
    "中大型MPV": "Mid-size MPV",
    "中型SUV": "Midsize SUV",
    "紧凑型SUV": "Compact SUV",
    "手自一体变速箱(AT)": "Automatic Manual Transmission (AT)",
    "前置后驱": "Front Engine Rear Drive",
    "前置前驱": "Front Engine Front Drive",
    "前置四驱": "Front Engine 4WD",
    "多连杆式独立悬架": "Multi-link Independent Suspension",
    "电动助力": "Electric Power Steering",
    "承载式": "Unibody",
    "通风盘式": "Ventilated Disc",
    "盘式": "Disc",
    "电子驻车": "Electronic Parking Brake",
    "无": "None",
    "铝合金": "Aluminum Alloy",
    "国VI": "China VI",
    "DOHC": "DOHC",
    "SOHC": "SOHC",
    "直喷": "Direct Injection",
    "北京奔驰": "Beijing Benz",
    "奥迪(进口)": "Audi (Imported)",
    "广汽丰田": "GAC Toyota",
    "上汽通用别克": "SAIC-GM Buick",
    "保时捷": "Porsche",
    "大众(进口)": "Volkswagen (Imported)",
    "奇瑞汽车": "Chery Automobile",
    
    # Additional values
    "12期": "12 Periods",
    "24期": "24 Periods",
    "36期": "36 Periods",
    "48期": "48 Periods",
    "分期": "Installment",
    "上牌": "Registration",
    "提车": "Pickup",
    "奔驰C级 2019款 C 260 运动版": "Mercedes-Benz C-Class 2019 C 260 Sport",
    "31.08万": "310,800 CNY",
    "1.5T 184马力 L4": "1.5T 184 HP L4",
    "9挡手自一体": "9-Speed Automatic Manual",
    "4门5座三厢车": "4-Door 5-Seat Sedan",
    "三年不限公里": "3 Years Unlimited Kilometers",
    "万": "10,000",
    "马力": "HP",
    "轻松开回家 首付4.08万 月供3071元": "Drive home easily, down payment 40,800, monthly payment 3,071 CNY",
    "根据汽车之家大数据分析，价格符合相似车源的平均报价。您可以结合这辆车的车龄、里程、配置和车况，来判断价格情况。": "According to Autohome big data analysis, the price matches the average price of similar vehicles. You can judge the price situation by combining the vehicle's age, mileage, configuration and condition.",
    "中山市中型车销量榜第1名": "Zhongshan City Midsize Car Sales Rank #1",
    "奔驰C级 2019款 C 260 运动版": "Mercedes-Benz C-Class 2019 C 260 Sport",
    "9挡手自一体": "9-Speed Automatic Manual",
    "4门5座三厢车": "4-Door 5-Seat Sedan",
    "三年不限公里": "3 Years Unlimited Kilometers",
    "1.5T 184马力 L4": "1.5T 184 HP L4",
    "95号": "95 Octane",
    "外观：漆面保养良好，车身结构无修复，无重大事故。 内饰：干净整洁。安全指示灯正常，气囊等被动安全项正常，车辆内电子器件使用良好， 车内静态动态设备完善。 驾驶：车辆点火、起步、提速、过弯、减速、制动均无问题，加速迅猛，动力输出平稳舒 适,无怠速抖动。 整体：整体车况一般。车体骨架结构无变形扭曲、无火烧泡水痕迹。车身有喷漆痕迹，整体漆面良好，排除大事故车辆。视野宽阔，练手选择，空间宽敞明亮通风性好，适合家庭代步车。": "Exterior: Paint surface well maintained, body structure has no repairs, no major accidents. Interior: Clean and tidy. Safety indicators normal, airbags and other passive safety items normal, vehicle electronics working well, static and dynamic equipment complete. Driving: Vehicle ignition, starting, acceleration, cornering, deceleration, braking all without problems, rapid acceleration, smooth and comfortable power output, no idle shaking. Overall: Overall vehicle condition is average. Body frame structure has no deformation or distortion, no fire or water damage. Body has paint marks, overall paint surface is good, excluding major accident vehicles. Wide field of view, good for practice, spacious and bright interior with good ventilation, suitable for family commuting.",
    "中山, 西区": "Zhongshan, West District",
}


def translate_text(text):
    """Translate Chinese text to English if translation exists."""
    if isinstance(text, str):
        # Check if text is in translations
        if text in TRANSLATIONS:
            return TRANSLATIONS[text]
        # Try to translate common patterns
        # Replace "万" with "10,000" in price contexts
        if "万" in text and any(char.isdigit() for char in text):
            # This is likely a price, keep as is for now
            pass
        # For descriptions, keep original (too complex to translate automatically)
        # Return original if no exact match
        return text
    return text


def translate_dict(obj):
    """Recursively translate Chinese text in dictionary."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                result[key] = translate_dict(value)
            elif isinstance(value, str):
                result[key] = translate_text(value)
            else:
                result[key] = value
        return result
    elif isinstance(obj, list):
        return [translate_dict(item) for item in obj]
    else:
        return obj


def main():
    """Translate first car from example.txt."""
    example_file = Path(__file__).parent.parent / "example.txt"
    
    with open(example_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get first car
    first_car = data['result'][0]
    
    # Translate
    translated_car = translate_dict(first_car)
    
    # Output translated JSON
    output_file = Path(__file__).parent.parent / "translated_car.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_car, f, indent=2, ensure_ascii=False)
    
    print("Translated car data saved to translated_car.json")
    print("\n=== Translated Car Data ===")
    print(json.dumps(translated_car, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
