#运行需要 requests bs4 openpyxl chardet pypinyin 库
import GetWeatherData
import String2Pinyin
if __name__ == '__main__':
    city = input("请输入城市名(例：深圳)：")
    city = String2Pinyin.String2Pinyin(city)
    GetWeatherData.GetWeatherData(city)