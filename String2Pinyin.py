from pypinyin import lazy_pinyin

def String2Pinyin(inputStr):
    # 移除所有的'市'字符
    modifiedStr = inputStr.replace('市', '')
    
    # 将剩余的字符串转换为拼音
    pinyinList = lazy_pinyin(modifiedStr)
    
    # 将拼音列表拼接成一个字符串，使用空格分隔
    pinyin = ''.join(pinyinList)
    
    return pinyin