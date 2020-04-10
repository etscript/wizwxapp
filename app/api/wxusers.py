#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, url_for, g, current_app
from app.utils.core import db
from app.utils.util import route
from app.utils.wxapp import create_token
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
import logging

bp = Blueprint("wxusers", __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@route(bp, '/wxusers/', methods=['POST'])
def create_wxuser():
    '''
    功能：登录或者注册一个新用户

    参数：user {
            code: data.code,
            username: userResult.encryptedData,
            password: userResult.iv,
            grant_type: 'password',
            auth_approach: 'wxapp'
        }

    返回格式:{'access_token': token,
                'nickname': account['nickName'],
                'openid': str(account['openId']),
                'avatarUrl':account['avatarUrl']}
    '''
    # 创建返回内容模板
    res = ResMsg()
    user = request.get_json()
    if not user:
        code = ResponseCode.InvalidParameter
        res.update(code = code, data = '没有收到微信小程序用户数据')
        return res.data
    is_validate, token = create_token(user, db)
    if not is_validate:
        code = ResponseCode.InvalidParameter
        res.update(code = code, data = '用户认证环节出错')
        return res.data

    # user = User()
    # user.from_dict(data, new_user=True)
    # db.session.add(user)
    # db.session.commit()

    code = ResponseCode.Success
    # HTTP协议要求201响应包含一个值为新资源URL的Location头部
    # response.headers['Location'] = url_for('api.cretae_wxuser', id=token["openid"])
    return token

# @bp.route('/users/<int:id>', methods=['GET'])
# def get_user(id):
#     '''返回一个用户'''
#     user = User.query.get_or_404(id)
#     if g.current_user == user:
#         return jsonify(user.to_dict(include_email=True))
#     # 如果是查询其它用户，添加 是否已关注过该用户 的标志位
#     data = user.to_dict()
#     data['is_following'] = g.current_user.is_following(user)
#     return jsonify(data)
