# tool1_天气查询.py
import requests,os
from dotenv import load_dotenv
load_dotenv()

def get_weather(city):
    """
    使用高德地图API查询天气
    流程：先通过城市名查行政区划编码(adcode)，再通过编码查天气
    """
    # ⚠️⚠️⚠️ 在这里填入你的高德 Key ⚠️⚠️⚠️
    API_KEY = os.getenv("API_KEY")

    if not API_KEY or "你的高德" in API_KEY:
        return "错误：请先在 tool1_天气查询.py 中配置高德 API Key"

    try:
        # 1. 地理编码：把“杭州”变成“330100”
        # 这里的 city 可能是 "杭州" 也可能是 "杭州市"，高德都能识别
        geo_url = f"https://restapi.amap.com/v3/config/district?keywords={city}&subdistrict=0&key={API_KEY}"
        geo_res = requests.get(geo_url, timeout=5).json()

        if geo_res['status'] != '1' or not geo_res['districts']:
            return f"未找到城市：{city}，请检查名称是否正确"

        adcode = geo_res['districts'][0]['adcode']
        full_city_name = geo_res['districts'][0]['name']

        # 2. 天气查询
        weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={API_KEY}"
        weather_res = requests.get(weather_url, timeout=5).json()

        if weather_res['status'] == '1' and weather_res['lives']:
            live = weather_res['lives'][0]
            # 组装一段自然的回复
            return (f"【{full_city_name}实时天气】\n"
                    f"天气现象：{live['weather']}\n"
                    f"当前气温：{live['temperature']}°C\n"
                    f"风向风力：{live['winddirection']}风 {live['windpower']}级\n"
                    f"空气湿度：{live['humidity']}%\n"
                    f"更新时间：{live['reporttime']}")
        else:
            return "天气查询服务暂无数据"

    except Exception as e:
        return f"接口调用出错: {str(e)}"


# --- 单元测试 ---
# 直接运行这个文件，看控制台能不能打印出天气
if __name__ == "__main__":
    print("正在测试高德API...")
    print(get_weather("杭州"))
    print("-" * 20)
    print(get_weather("北京"))