import requests
import json
import time

# 配置
BASE_URL = "http://127.0.0.1:8000/api/v1"
HEALTH_URL = "http://127.0.0.1:8000/health"
TIMEOUT = 60

def print_divider():
    """打印分隔线"""
    print("="*60)

def test_health_check():
    """测试健康检查接口"""
    print_divider()
    print("测试1：服务健康检查")
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 200:
            print(f"✅ 健康检查通过：{response.json()}")
            return True
        else:
            print(f"❌ 健康检查失败，状态码：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常：{str(e)}")
        return False

def test_generate_intro():
    """测试完整参数生成简介接口"""
    print_divider()
    print("测试2：完整参数生成产品简介")
    url = f"{BASE_URL}/generate-intro"
    
    # 测试数据
    test_data = {
        "product_info": {
            "title": "无线蓝牙耳机",
            "description": "蓝牙5.3技术，30小时续航，IPX7防水，主动降噪",
            "parameters": {
                "蓝牙版本": "5.3",
                "续航": "30小时",
                "防水等级": "IPX7"
            },
            "competitor_features": ["续航20小时", "无降噪功能", "防水IPX5"]
        },
        "market_info": {
            "country": "Россия",
            "audience": "18-35岁年轻人群",
            "target_language": "русский язык"
        }
    }
    
    try:
        # 发送请求
        start_time = time.time()
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=test_data,
            timeout=TIMEOUT
        )
        elapsed = round(time.time() - start_time, 2)
        
        # 解析响应
        print(f"请求耗时：{elapsed}秒")
        print(f"状态码：{response.status_code}")
        
        if response.status_code == 200:
            res_json = response.json()
            print(f"✅ 接口调用成功")
            print(f"   success: {res_json['success']}")
            print(f"   卖点数量：{len(res_json['key_features'])}")
            print(f"   简介内容：{res_json['product_intro'][:1000]}...")
            return res_json["success"]
        else:
            print(f"❌ 接口调用失败：{response.text}")
            return False
    except Exception as e:
        print(f"❌ 接口调用异常：{str(e)}")
        return False

if __name__ == "__main__":
    print(f"开始测试 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行测试
    health_ok = test_health_check()
    if health_ok:
        intro_ok = test_generate_intro()
    else:
        intro_ok = False
    
    # 汇总结果
    print_divider()
    print("测试汇总：")
    print(f"健康检查：{'✅ 通过' if health_ok else '❌ 失败'}")
    print(f"接口测试：{'✅ 通过' if intro_ok else '❌ 失败'}")
    print_divider()
    
    input("\n测试完成，按回车键退出...")