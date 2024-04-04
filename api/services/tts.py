# -*- coding: UTF-8 -*-
# Python 2.x引入httplib模块。
# import httplib
# Python 3.x引入http.client模块。
import http.client
# Python 2.x引入urllib模块。
# import urllib
# Python 3.x引入urllib.parse模块。
import urllib.parse
import json


def get_tts_url(token, text, format='mp3'):
    host = 'nls-gateway-cn-shanghai.aliyuncs.com'
    url = 'https://' + host + '/stream/v1/tts'
    appKey = '7UQEOhSzrOjZKk61'
    # 设置URL请求参数
    url = url + '?appkey=' + appKey
    url = url + '&token=' + token
    url = url + '&text=' + text
    url = url + '&format=' + format
    # url = url + '&sample_rate=' + str(sampleRate)
    # voice 发音人，可选，默认是xiaoyun。
    url = url + '&voice=' + 'zhishuo'
    # volume 音量，范围是0~100，可选，默认50。
    # url = url + '&volume=' + str(50)
    # speech_rate 语速，范围是-500~500，可选，默认是0。
    # url = url + '&speech_rate=' + str(0)
    # pitch_rate 语调，范围是-500~500，可选，默认是0。
    # url = url + '&pitch_rate=' + str(0)
    print(url)
    return url
