#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request, current_app
from app.utils.util import route, Redis
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import token_auth
import requests
import logging
import json
bp = Blueprint("companyitems", __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@bp.route('/company_items/', methods=['GET'])
@token_auth.login_required
def company_items():
    '''
    功能: 根据选择公司获取查询项（包括：信息个数，信息单价）

    参数: "company":"上海思华科技股份有限公司"

    返回格式: {
                code: 0,
                lang: "zh_CN",
                msg: "成功!",
                data: [{
                    "type": 'experience', // 体验版
                    "counts": 20, // 总的查询数
                    "price": 0.1 // 单价人民币
                    },
                    {
                    "type": 'complete', // 完整版
                    "counts": 200, // 总的查询数
                    "price": 0.1 // 单价人民币
                    }
                ]
            }

    '''
    # 创建返回内容模板
    res = ResMsg()
    # 获取公司全称
    word = request.args.get("company")
    if not word:
        code = ResponseCode.InvalidParameter
        res.update(code = code, data='请输入公司全称')
        return res.data


    data = [{
        "type": 'experience', # 体验版
        "counts": current_app.config.get('experience_counts'), # 总的查询数
        "price": current_app.config.get('experience_price') # 单价人民币
        },
        {
        "type": 'complete', # 完整版
        "counts": current_app.config.get('complete_counts'), # 总的查询数
        "price": current_app.config.get('complete_price') # 单价人民币
        }
    ]

    # 制作返回内容
    code = ResponseCode.Success
    res.update(code = code, data = data)
    return res.data

