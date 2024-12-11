# GetWeatherData.py

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from datetime import datetime, timedelta
import os
import chardet  # 用于检测编码
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def GetWeatherData(city):
    """
    获取指定城市最近30天的历史天气数据并保存为Excel文件。
    
    :param city: 城市名称，例如 'shenzhen'
    """
    # 计算近30天起止日期
    today = datetime.now()
    start_date = today - timedelta(days=30)
    
    # 根据起止日期计算需要请求的月份列表
    months_to_fetch = _get_month_list(start_date, today)

    all_data = []
    for yyyymm in months_to_fetch:
        logging.info(f"Fetching data for {yyyymm}...")
        html_content = _fetch_monthly_data(city, yyyymm)
        if html_content:
            month_data = _parse_html_to_data(html_content)
            all_data.extend(month_data)
        else:
            logging.warning(f"Failed to fetch data for {yyyymm}")
    
    # 根据日期筛选近30天的数据
    filtered_data = _filter_data_by_date(all_data, start_date, today)

    # 写入Excel，并传递city参数
    _write_to_excel(filtered_data, city)


def _get_month_list(start_date, end_date):
    """
    获取从start_date到end_date之间所有涉及的年月列表，格式为'YYYYMM'。
    
    :param start_date: 起始日期
    :param end_date: 结束日期
    :return: 包含所有涉及年月的字符串列表
    """
    year_months = []
    start_ym = start_date.year * 100 + start_date.month
    end_ym = end_date.year * 100 + end_date.month
    for ym in range(start_ym, end_ym + 1):
        year = ym // 100
        month = ym % 100
        if month > 12:
            year += 1
            month = 1
        year_months.append(f"{year}{str(month).zfill(2)}")
    return year_months


def _fetch_monthly_data(city, yyyymm):
    """
    获取指定城市和年月的历史天气页面内容，并保存为HTML文件。
    
    :param city: 城市名称，例如 'shenzhen'
    :param yyyymm: 年月，格式为 'YYYYMM'
    :return: 返回HTML内容和编码
    """
    url = f"http://www.tianqihoubao.com/lishi/{city}/month/{yyyymm}.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()  # 检查请求是否成功

        # 使用chardet自动检测编码
        detected_encoding = chardet.detect(response.content)
        encoding = detected_encoding['encoding']
        confidence = detected_encoding['confidence']
        logging.info(f"Detected encoding for {yyyymm}: {encoding} (confidence: {confidence})")

        if encoding:
            # 保存HTML内容用于调试，文件命名为 {city}{yyyymm}.html
            if not os.path.exists("output"):
                os.mkdir("output")
            html_filename = f"{city}{yyyymm}.html"
            with open(f"output/{html_filename}", 'wb') as f:
                f.write(response.content)
            
            return response.content, encoding
        else:
            logging.error(f"无法检测到{yyyymm}的编码，跳过此月。")
            return None, None
    except requests.RequestException as e:
        logging.error(f"请求{url}时出错: {e}")
        return None, None


def _parse_html_to_data(html_content):
    """
    解析HTML内容，提取天气数据。
    
    :param html_content: HTML内容和编码
    :return: 解析后的天气数据列表
    """
    if not html_content[0]:
        return []
    
    content, encoding = html_content
    # 使用正确的编码解析HTML
    soup = BeautifulSoup(content, 'lxml', from_encoding=encoding)
    
    wdetail_div = soup.find('div', class_='wdetail')
    if not wdetail_div:
        logging.warning("未找到.wdetail对应的div。请检查HTML结构。")
        return []

    table = wdetail_div.find('table', class_='b')
    if not table:
        logging.warning("未在.wdetail下找到table.b，请检查HTML结构。")
        return []

    rows = table.find_all('tr')
    data = []
    for tr in rows[1:]:  # 第一行是表头，从第二行开始数据行
        cols = tr.find_all(['td', 'th'])
        col_texts = [c.get_text(strip=True) for c in cols]
        # 进一步清洗空白字符和换行
        col_texts = [' '.join(text.split()) for text in col_texts]
        # col_texts格式大致为：[日期, 天气状况(白天/夜间), 最高/最低气温, 风力风向(白天/夜间)]
        if len(col_texts) == 4:
            date_str = col_texts[0]
            # 打印日期字符串用于调试
            logging.debug(f"Parsing date string: '{date_str}'")
            try:
                # 尝试解析日期字符串
                date_dt = datetime.strptime(date_str, "%Y年%m月%d日")
            except ValueError as ve:
                logging.error(f"解析日期字符串'{date_str}'时出错: {ve}")
                continue  # 跳过无法解析的行
            
            weather_day_night = col_texts[1]
            temperature = col_texts[2]
            wind = col_texts[3]

            # 拆分最高/最低气温
            if '/' in temperature:
                high_temp, low_temp = [t.strip() for t in temperature.split('/', 1)]
            else:
                high_temp, low_temp = temperature, ''

            # 拆分风力风向
            if '/' in wind:
                wind_day, wind_night = [w.strip() for w in wind.split('/', 1)]
            else:
                wind_day, wind_night = wind, ''

            data.append({
                'date': date_dt,
                'weather_day_night': weather_day_night,
                'high_temp': high_temp,
                'low_temp': low_temp,
                'wind_day': wind_day,
                'wind_night': wind_night
            })
    return data


def _filter_data_by_date(data, start_date, end_date):
    """
    筛选出日期在起止范围内的数据。
    
    :param data: 所有天气数据列表
    :param start_date: 起始日期
    :param end_date: 结束日期
    :return: 筛选后的天气数据列表
    """
    # 筛选出date在start_date与end_date之间的数据
    filtered = [d for d in data if start_date <= d['date'] <= end_date]
    # 按日期排序
    filtered.sort(key=lambda x: x['date'])
    logging.info(f"Filtered data count: {len(filtered)}")
    return filtered


def _write_to_excel(data, city):
    """
    将天气数据写入Excel文件。
    
    :param data: 筛选后的天气数据列表
    :param city: 城市名称，例如 'shenzhen'
    """
    if not data:
        logging.warning("没有可写入的数据。")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Last30DaysWeather"
    # 写入表头
    ws.append(["日期", "天气状况(白天/夜间)", "最高气温", "最低气温", "风力风向(白天)", "风力风向(夜间)"])

    # 写入数据
    for row_data in data:
        ws.append([
            row_data['date'].strftime("%Y-%m-%d"),
            row_data['weather_day_night'],
            row_data['high_temp'],
            row_data['low_temp'],
            row_data['wind_day'],
            row_data['wind_night']
        ])

    # 保存文件，命名为 {city}Last30DaysWeather.xlsx
    if not os.path.exists("output"):
        os.mkdir("output")
    excel_filename = f"{city}Last30DaysWeather.xlsx"
    wb.save(f'output/{excel_filename}')
    logging.info(f"数据已成功写入 output/{excel_filename}")


if __name__ == '__main__':
    GetWeatherData('shenzhen')
