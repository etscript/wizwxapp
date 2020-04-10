# -*- coding: UTF-8 -*-
from weixin.oauth2 import OAuth2AuthExchangeError
from weixin.lib.wxcrypt import WXBizDataCrypt
from app.models.model import WXUser as User
from weixin import WXAPPAPI
import time
import jwt

def get_wxapp_userinfo(encrypted_data, iv, code):
    '''
        功能：
        通过encrypted_data, iv, code获取到微信用户的信息 user_info 和 session_key

        参数：
        encrypted_data  小程序端调用 wx.getUserInfo 获取 包括敏感数据在内的完整用户信息的加密数据
        iv 小程序端调用 wx.getUserInfo 获取 加密算法的初始向量
        code 小程序端调用 wx.login() 获取 临时登录凭证code 

        返回格式：
        user_info: {"openId":"xxxxxxx",.......}, session_key
    '''
    appid = 'wx15fa925381f617dd'
    secret = 'd3b2a8beb372b2165fee7e844d0282b0'
    api = WXAPPAPI(appid=appid, app_secret=secret)
    try:
        session_info = api.exchange_code_for_session_key(code=code)
    except OAuth2AuthExchangeError as e:
        print('111')
        print(e)
        # raise Unauthorized(e.code, e.description)
        return 401
    session_key = session_info.get('session_key')
    crypt = WXBizDataCrypt(appid, session_key)
    user_info = crypt.decrypt(encrypted_data, iv)
    return user_info, session_key

def verify_wxapp(encrypted_data, iv, code, db_conn):
    '''
        功能：
        通过get_wxapp_userinfo函数获取到user_info和session_key
        根据user_info中的openId判断是否新用户
        新用户直接注册，然后返回，老用户直接返回

        参数：
        encrypted_data,iv,code 同 get_wxapp_userinfo方法
        db_conn 数据库操作对象

        返回格式：
        user_info: {"openId":"xxxxxxx",.......}, session_key
    '''
    user_info, session_key = get_wxapp_userinfo(encrypted_data, iv, code)
    openid = user_info.get('openId', None)
    print(user_info)
    if openid:
        #user = User.query.get_or_404(openid)
        user = User.query.get(openid)
        if not user:
            user = User()
            user.from_dict(user_info)
            db_conn.session.add(user)
            db_conn.session.commit()
    return user_info, session_key

def create_token(user, db_conn):
    '''
        功能：
        获得前端的user数据，返回用户信息

        参数：
        user  {
                code: data.code,
                username: userResult.encryptedData,
                password: userResult.iv,
                grant_type: 'password',
                auth_approach: 'wxapp'
            }
        db_conn 数据库操作对象

        返回格式：
        非正常返回   False, {}
        正常返回     True, {'access_token': token,
                        'nickname': account['nickName'],
                        'openid': str(account['openId']),
                        'avatarUrl':account['avatarUrl']}
    '''
    # verify basic token
    print(user)
    approach = user["auth_approach"]
    username = user["username"]
    password = user["password"]
    code = user['code']
    
    if approach == 'wxapp':
        account, session_key = verify_wxapp(username, password, code, db_conn)
    if not account:
        return False, {}

    payload = {
        "iss": 'wxapp',
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400 * 7,
        "aud": 'flask',
        "sub": str(account['openId']),
        "nickname": account['nickName'],
        "scopes": ['open']
    }
    token = jwt.encode(payload, 'secret', algorithm='HS256')
    # save token openid session_key
    # sql_body = UserWXModel(id=token, openid=account['openId'],
    #                 session_key=session_key,created_time=datetime.now(),
    #                 updated_time=datetime.now())
    # db.session.add(sql_body)
    # db.session.commit()

    return True, {'access_token': token,
                  'nickname': account['nickName'],
                  'openid': str(account['openId']),
                  'avatarUrl':account['avatarUrl']}
