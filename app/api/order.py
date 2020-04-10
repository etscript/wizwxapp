#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import jsonify, request, current_app
from app.utils.util import route, Redis
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import token_auth
import requests
import logging
import json
from app.api import bp
logger = logging.getLogger(__name__)

@bp.route('/order_list', methods=['GET'])
@token_auth.login_required
def order_list():
    '''
    功能: 公司搜索，模糊匹配

    参数: "search":"上海思华"

    返回格式: {
        "code": 0,
        "data": [
            {
                "base": "上海",
                "companyType": 1,
                "estiblishTime": "2000-08-15 00:00:00.0",
                "id": 1032774619,
                "legalPersonName": "孙逸浪",
                "name": "<em>上海思华</em>科技股份有限公司",
                "regCapital": "10750万人民币",
                "type": 1
            },
            {
                "base": "上海",
                "companyType": 1,
                "estiblishTime": "1994-05-05 00:00:00.0",
                "id": 1136050774,
                "legalPersonName": "陈愉",
                "name": "<em>上海思华</em>咨询有限公司",
                "regCapital": "15万美元",
                "type": 1
            },...],
            "lang": "zh_CN",
            "msg": "成功"
        }

    '''
    # 创建返回内容模板
    res = ResMsg()
    # 获取公司名称关键字
    word = request.args.get("search")
    if not word:
        code = ResponseCode.InvalidParameter
        res.update(code = code, data='请输入公司名称关键字')
        return res.data
    # 从Redis获取
    req = Redis.read(word+"company_list")
    # 如果Redis中有记录，转换类型。如果没有历史记录，请求天眼查获取，并写入Redis。
    if req:
        req = json.loads(req)
    else:
        # 头部内容，包括天眼查token
        header = {"Authorization":current_app.config.get('tianyancha_token'),
                    "Content-Type":"application/x-www-form-urlencoded"}
        # 天眼查api地址
        url = current_app.config.get('tianyancha_search_company_url') + word
        # 请求返回
        req = requests.get(url, headers=header)
        # 错误内容提示稍后再试
        if req.status_code != 200:
            code = ResponseCode.InvalidParameter
            res.update(code = code, data="请稍安勿躁，休息片刻再试。")
            return res.data
        req= req.json()
        Redis.write(word+"company_list", json.dumps(req), 86400)

    # 制作返回内容
    code = ResponseCode.Success
    res.update(code = code, data = req["result"]["items"])
    return res.data

