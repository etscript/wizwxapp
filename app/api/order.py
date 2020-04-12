#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import jsonify, request, current_app, g
from app.utils.util import route, Redis
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import token_auth
import requests
import logging
import json
import time
from app.api import bp
from app.utils.core import db
from app.models.model import Order, WXUser
logger = logging.getLogger(__name__)

# 生成订单号
def get_order_code():
    order_no = str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))+ str(time.time()).replace('.', '')[-7:]
    return order_no

@bp.route('/orders', methods=['GET'])
@token_auth.login_required
def orders():
    '''
    功能: 查询某个人的所有订单

    参数: 无

    返回格式: {
        "code": 0,
        "lang": "zh_CN",
        "msg": "成功!",
        "data": [{
            "status": "complete",
            "company": "上海思华科技股份有限公司上海思华科技股份有限公司",
            "create": "2000-08-15 00:00:00.0",
            "id": 234,
            "price": "39.9人民币",
            "email": "example@qq.com",
            "code": 4.246256245624246e+35
            },
            {
            "status": "checking",
            "company": "上海思华科技股份有限公司",
            "create": "2000-08-15 00:00:00.0",
            "id": 234,
            "price": "39.9人民币",
            "email": "example@qq.com",
            "code": 23456254
            }
        ]
    }

    '''
    # 创建返回内容模板
    res = ResMsg()
    # 获取用户信息
    user = g.current_user
    if not user:
        code = ResponseCode.InvalidParameter
        res.update(code = code, data='未找到用户信息')
        return res.data
    orders = Order.query.filter(Order.wxuser_openid == user.openid).all()
    data = Order.to_collection_dict(orders)

    # 制作返回内容
    return ResMsg(data = data).data

@bp.route('/send_order', methods=['POST'])
@token_auth.login_required
def send_order():
    '''
    功能: 小程序下单

    参数: {
      "status": "complete", // 已完成
      "company": '上海思华科技股份有限公司',
      "price": 39.9,
    }

    返回格式: {
      "status": "complete", // 已完成
      "company": '上海思华科技股份有限公司',
      "create": "2000-08-15 00:00:00.0",
      "id": 234,
      "price": 39.9,
      "code": "sdasdasdsadsadsadasd" // 订单号,
    }
    '''
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        data = 'You must post JSON data.'
        return ResMsg(code=code, data=data).data

    order = Order()
    data["wxuser_openid"] = g.current_user.to_dict()["openid"]
    data["code"] = get_order_code()
    order.from_dict(data)
    
    db.session.add(order)
    db.session.commit()

    # 制作返回内容
    return ResMsg(data = data).data

@bp.route('/order/<int:id>', methods=['PUT'])
@token_auth.login_required
def edit_order(id):
    '''
    功能: 小程序订单状态修改

    参数: 
    <int:id> 订单的id
    {
      "status": "状态", // complete, checking
      "result": "生成文件的地址" //绝对路径
    }

    返回格式: {
      "status": "complete", // 已完成
      "company": '上海思华科技股份有限公司',
      "create": "2000-08-15 00:00:00.0",
      "complete": "2000-08-15 00:00:00.0",
      "id": 234,
      "price": 39.9,
      "code": "sdasdasdsadsadsadasd" // 订单号,
    }
    '''
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        data = 'You must post JSON data.'
        return ResMsg(code=code, data=data).data
    
    order = Order.query.get_or_404(id)
    order.from_dict(data)
    db.session.commit()

    # 制作返回内容
    return ResMsg(data = data).data

@bp.route('/order/<int:id>/mail', methods=['POST'])
@token_auth.login_required
def order_send_mail(id):
    '''
    功能: 小程序订单任务完成，通过邮件发送结果

    参数: 
    <int:id> 订单的id
    {
      "type": "尽调报告结果",
      "email": "sadasd@asdasd.com"
    }

    返回格式: {
      "status": "complete", // 已完成
      "company": '上海思华科技股份有限公司',
      "create": "2000-08-15 00:00:00.0",
      "complete": "2000-08-15 00:00:00.0",
      "id": 234,
      "price": 39.9,
      "code": "sdasdasdsadsadsadasd" // 订单号,
    }
    '''
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        data = 'You must post JSON data.'
        return ResMsg(code=code, data=data).data
        
    order = Order.query.get_or_404(id)
    result_address = order.to_dict()["result"]
    email = data["email"] if data["email"] else g.current_user.email
    send_email(data["type"] + " : " + order.company,
               sender=current_app.config['MAIL_SENDER'],
               recipients=email,
               text_body='text_body',
               html_body="<p>Dear,</p>")

    # 制作返回内容
    return ResMsg(data = data).data

