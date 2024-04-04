import json
import time

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from flask import request, redirect, current_app
from flask_restful import Resource

from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required
from extensions.ext_redis import redis_client
from libs.login import login_required
from services.tts import get_tts_url

cache_key = "aliyun_token"


def get_token_from_cache():
    """
    从Redis缓存中获取令牌。
    """
    token_info = redis_client.get(cache_key)
    return json.loads(token_info) if token_info else None


def save_token_to_cache(token_info, expire_in):
    """
    将令牌存储到Redis缓存中。
    这里的expire_in是令牌的有效期，单位秒。
    """
    # 防止令牌在Redis中过期前刚好被请求，给一定缓冲时间，例如减少60秒
    expire_in = max(expire_in - 60, 1)
    redis_client.setex(cache_key, expire_in, json.dumps(token_info))


def request_new_token():
    """
    从服务器请求新的令牌。
    """
    client = AcsClient(
        current_app.config.get('ALIYUN_AK_ID'),
        current_app.config.get('ALIYUN_AK_SECRET'),
        "cn-shanghai"
    )

    request = CommonRequest()
    request.set_method('POST')
    request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
    request.set_version('2019-02-28')
    request.set_action_name('CreateToken')

    response = client.do_action_with_exception(request)
    response_dict = json.loads(response)

    token = response_dict['Token']['Id']
    expire_time = response_dict['Token']['ExpireTime']
    return {
        "token": token,
        "expireTime": expire_time
    }


def get_token():
    """
    获取令牌。首先尝试从Redis缓存中获取，如果没有找到或令牌已过期，
    则向服务器请求新的令牌，并将其保存到Redis缓存中。
    """
    # 尝试从缓存中获取令牌
    token_info = get_token_from_cache()
    if token_info and token_info['expireTime'] > time.time():
        # 检查令牌是否过期
        return token_info['token']
    else:
        # 缓存失效，请求新的令牌
        token_info = request_new_token()
        # 计算令牌的有效期
        expire_in = int(token_info['expireTime']) - int(time.time())
        # 存储新的令牌到缓存中
        save_token_to_cache(token_info, expire_in)
        return token_info['token']


class TarAppTtsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        text = request.args.get('text', default='', type=str)
        token = get_token()
        url = get_tts_url(token, text)

        return redirect(url, code=302)

        # response = {
        #     'url': url
        # }
        #
        # return response, 200


api.add_resource(TarAppTtsApi, '/tar/app/tts')
