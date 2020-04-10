import logging
import random
import uuid
import os
from flask import Blueprint, jsonify, session, request, current_app
from datetime import datetime, timedelta
from decimal import Decimal

from app.api.tree import Tree
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.util import route, Redis, CaptchaTool, PhoneTool
from app.utils.auth import Auth, login_required
from app.api.report import excel_write, word_write, pdf_write
from app.api.wx_login_or_register import get_access_code, get_wx_user_info, wx_login_or_register
from app.api.phone_login_or_register import SendSms, phone_login_or_register
from app.celery import add, flask_app_context

from wechatpy import WeChatClient, parse_message
from wechatpy.utils import check_signature
from wechatpy.session.redisstorage import RedisStorage
from app.utils.wechat_utils import create_flag, \
                handleWxEvent, client, isFlagExist,\
                    make_qrcode, get_all_args
from elasticsearch import Elasticsearch
es = Elasticsearch()

bp = Blueprint("test", __name__, url_prefix='/api')

logger = logging.getLogger(__name__)
# -----------------原生蓝图路由---------------#


# @bp.route('/logs', methods=["GET"])
# def test_logger():
#     """
#     测试自定义logger
#     :return:
#     """
#     logger.info("this is info")
#     logger.debug("this is debug")
#     logger.warning("this is warning")
#     logger.error("this is error")
#     logger.critical("this is critical")
#     return "ok"

@route(bp, '/get_qrcode/', methods=['GET'])
def get_qrcode():
    res = ResMsg()
    # 创建flag
    wechat_flag = create_flag()
    # 创建微信带参二维码
    # 创建一天有效期的二维码, 参数使用字符串而不是数字id
    res_qrcode = make_qrcode(client, scene_str = wechat_flag)
    # 创建二维码地址
    url = client.qrcode.get_url(res_qrcode['ticket'])

    res.update(data=dict(qrcode_url = url,
                wechat_flag = wechat_flag)) 
    return res.data

@route(bp, '/wechat_verify/',methods=['GET','POST'])
def wechat_verify():
    '''
    用来处理微信服务器对本后台的验证，GET方法。
    :return:
    '''
    # POST 方式用于接受被动消息
    if request.method == 'POST':
        msg = parse_message(request.get_data())
        # print("开发者服务收到的消息:", msg.scene_id)
        # 处理方法
        handleWxEvent(msg)
        return 'ok'
    
    if request.method == 'GET':
        # 获取参数
        rq_dict = request.args
        if len(rq_dict) == 0:
            return ""
        tuple_args = get_all_args(rq_dict)
        token = '123456'
        try:
            check_signature(token, tuple_args[1], tuple_args[2], tuple_args[3])
        except InvalidSignatureException as e:
            logger.error(e,exc_info=True)
            return ''
        else:
            return tuple_args[0]

@route(bp, '/check_login/',methods=['GET'])
def check_login():
    res = ResMsg()
    rq_dict = request.args
    # 获取随机字符串
    wechat_flag = rq_dict.get("wechat_flag")  
    # 判断这个wechat_flag的用户是否关注
    if isFlagExist(wechat_flag) and len(rq_dict) != 0:
        code = ResponseCode.Success
        data = {"result":"yes", "user":isFlagExist(wechat_flag)}
    elif len(rq_dict) == 0:
        code = ResponseCode.InvalidParameter
        data = None
    else:
        code = ResponseCode.NoResourceFound
        data = {"result":"no"}

    res.update(code=code, data=data)
    return res.data

@route(bp, '/logout/',methods=['PUT'])
@login_required
def check_logout():
    res = ResMsg()
    user_id = session["user_name"]
    Redis.delete(user_id)
    res.update(data={"result":"yes"})
    return res.data


@route(bp, '/addDataset/',methods=['PUT'])
@login_required
def add_dataset():
    req_json = request.get_json(force=True)
    
    res = ResMsg()
    result = es.index(index='news', doc_type='politics', body=req_json)
    res.update(data=result)
    return res.data

@route(bp, '/deleteDataset/',methods=['DELETE'])
@login_required
def delete_dataset():
    req_json = request.get_json(force=True)
    id = req_json.get("id")
    if not id:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    res = ResMsg()
    result = es.delete(index='news', doc_type='politics', id=id)
    res.update(data=result)
    return res.data

@route(bp, '/editDataset/',methods=['POST'])
@login_required
def edit_dataset():
    req_json = request.get_json(force=True)
    id = req_json.get("id")
    if not id:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    res = ResMsg()
    # body = req_json.pop("id")
    body = req_json
    result = es.update(index='news', doc_type='politics', body={"doc":body}, id=str(id))
    res.update(data=result)
    return res.data

@route(bp, '/getDataset/',methods=['GET'])
def get_dataset():
    res = ResMsg()
    rq_dict = request.args
    if len(rq_dict) == 0:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    # 获取查询的关键字
    keyword = rq_dict.get("keyword")  
    # 制作查询的DSL语句，使用match指定全文索引
    # 索引的字段是title，内容是keyword的值
    dsl = {
        'query': {
            'match': {
                'title': keyword
            }
        }
    }
    result = es.search(index='news', body=dsl)
    res.update(data=result)
    return res.data

@route(bp, '/listDataset/',methods=['GET'])
def list_dataset():
    res = ResMsg()
    rq_dict = request.args
    if len(rq_dict) == 0:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    # 获取查询index的所有数据
    keyword = rq_dict.get("keyword")  
    result = es.search(index=keyword)
    res.update(data=result)
    return res.data

def init_dataset():
    mapping = {
        "properties":{
            "title":{
                "type":"text",
                "analyzer":"ik_max_word",
                "search_analyzer":"ik_max_word"
            }
        }
    }
    es.indices.create(index='news', ignore=400)
    result = es.indices.put_mapping(index='news', doc_type='politics', body=mapping)
    return result

# --------------使用自定义封装蓝图路由--------------------#


@route(bp, '/packedResponse', methods=["GET"])
def test_packed_response():
    """
    测试响应封装
    :return:
    """
    res = ResMsg()
    test_dict = dict(name="zhang", age=18)
    # 此处只需要填入响应状态码,即可获取到对应的响应消息
    res.update(code=ResponseCode.Success, data=test_dict)
    # 此处不再需要用jsonify，如果需要定制返回头或者http响应如下所示
    # return res.data,200,{"token":"111"}
    return res.data


@route(bp, '/typeResponse', methods=["GET"])
def test_type_response():
    """
    测试返回不同的类型
    :return:
    """
    res = ResMsg()
    now = datetime.now()
    date = datetime.now().date()
    num = Decimal(11.11)
    test_dict = dict(now=now, date=date, num=num)
    # 此处只需要填入响应状态码,即可获取到对应的响应消息
    res.update(code=ResponseCode.Success, data=test_dict)
    # 此处不再需要用jsonify，如果需要定制返回头或者http响应如下所示
    # return res.data,200,{"token":"111"}
    return res.data


# --------------Redis测试封装--------------------#

@route(bp, '/testRedisWrite', methods=['GET'])
def test_redis_write():
    """
    测试redis写入
    """
    # 写入
    Redis.write("test_key", "test_value", 60)
    return "ok"


@route(bp, '/testRedisRead', methods=['GET'])
def test_redis_read():
    """
    测试redis获取
    """
    data = Redis.read("test_key")
    return data


# -----------------图形验证码测试---------------------------#

@route(bp, '/testGetCaptcha', methods=["GET"])
def test_get_captcha():
    """
    获取图形验证码
    :return:
    """
    res = ResMsg()
    new_captcha = CaptchaTool()
    img, code = new_captcha.get_verify_code()
    res.update(data=img)
    session["code"] = code
    return res.data


@route(bp, '/testVerifyCaptcha', methods=["POST"])
def test_verify_captcha():
    """
    验证图形验证码
    :return:
    """
    res = ResMsg()
    obj = request.get_json(force=True)
    code = obj.get('code', None)
    s_code = session.get("code", None)
    print(code, s_code)
    if not all([code, s_code]):
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    if code != s_code:
        res.update(code=ResponseCode.VerificationCodeError)
        return res.data
    return res.data


# --------------------JWT测试-----------------------------------------#

@route(bp, '/testLogin', methods=["POST"])
def test_login():
    """
    登陆成功获取到数据获取token和刷新token
    :return:
    """
    res = ResMsg()
    obj = request.get_json(force=True)
    user_name = obj.get("name")
    # 未获取到参数或参数不存在
    if not obj or not user_name:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data

    if user_name == "qin":
        # 生成数据获取token和刷新token
        access_token, refresh_token = Auth.encode_auth_token(user_id=user_name)

        data = {"access_token": access_token.decode("utf-8"),
                "refresh_token": refresh_token.decode("utf-8")
                }
        res.update(data=data)
        return res.data
    else:
        res.update(code=ResponseCode.AccountOrPassWordErr)
        return res.data


@route(bp, '/testGetData', methods=["GET"])
@login_required
def test_get_data():
    """
    测试登陆保护下获取数据
    :return:
    """
    res = ResMsg()
    name = session.get("user_name")
    data = "{}，你好！！".format(name)
    res.update(data=data)
    return res.data


@route(bp, '/testRefreshToken', methods=["GET"])
def test_refresh_token():
    """
    刷新token，获取新的数据获取token
    :return:
    """
    res = ResMsg()
    refresh_token = request.args.get("refresh_token")
    if not refresh_token:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    payload = Auth.decode_auth_token(refresh_token)
    # token被串改或过期
    if not payload:
        res.update(code=ResponseCode.PleaseSignIn)
        return res.data

    # 判断token正确性
    if "user_id" not in payload:
        res.update(code=ResponseCode.PleaseSignIn)
        return res.data
    # 获取新的token
    access_token = Auth.generate_access_token(user_id=payload["user_id"])
    data = {"access_token": access_token.decode("utf-8"), "refresh_token": refresh_token}
    res.update(data=data)
    return res.data


# --------------------测试Excel报表输出-------------------------------#

@route(bp, '/testExcel', methods=["GET"])
def test_excel():
    """
    测试excel报表输出
    :return:
    """
    res = ResMsg()
    report_path = current_app.config.get("REPORT_PATH", "./report")
    file_name = "{}.xlsx".format(uuid.uuid4().hex)
    path = os.path.join(report_path, file_name)
    path = excel_write(path)
    path = path.lstrip(".")
    res.update(data=path)
    return res.data


# --------------------测试Word报表输出-------------------------------#

@route(bp, '/testWord', methods=["GET"])
def test_word():
    """
    测试word报表输出
    :return:
    """
    res = ResMsg()
    report_path = current_app.config.get("REPORT_PATH", "./report")
    file_name = "{}.docx".format(uuid.uuid4().hex)
    path = os.path.join(report_path, file_name)
    path = word_write(path)
    path = path.lstrip(".")
    res.update(data=path)
    return res.data


# --------------------测试无限层级目录树-------------------------------#

@route(bp, '/testTree', methods=["GET"])
def test_tree():
    """
    测试无限层级目录树
    :return:
    """
    res = ResMsg()
    data = [
        {"id": 1, "father_id": None, "name": "01"},
        {"id": 2, "father_id": 1, "name": "0101"},
        {"id": 3, "father_id": 1, "name": "0102"},
        {"id": 4, "father_id": 1, "name": "0103"},
        {"id": 5, "father_id": 2, "name": "010101"},
        {"id": 6, "father_id": 2, "name": "010102"},
        {"id": 7, "father_id": 2, "name": "010103"},
        {"id": 8, "father_id": 3, "name": "010201"},
        {"id": 9, "father_id": 4, "name": "010301"},
        {"id": 10, "father_id": 9, "name": "01030101"},
        {"id": 11, "father_id": 9, "name": "01030102"},
    ]

    new_tree = Tree(data=data)

    data = new_tree.build_tree()

    res.update(data=data)
    return res.data


# --------------------测试微信登陆注册-------------------------------#

@route(bp, '/testWXLoginOrRegister', methods=["GET"])
def test_wx_login_or_register():
    """
    测试微信登陆注册
    :return:
    """
    res = ResMsg()
    code = request.args.get("code")
    flag = request.args.get("flag")
    # 参数错误
    if code is None or flag is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    # 获取微信用户授权码
    access_code = get_access_code(code=code, flag=flag)
    if access_code is None:
        res.update(code=ResponseCode.WeChatAuthorizationFailure)
        return res.data
    # 获取微信用户信息
    wx_user_info = get_wx_user_info(access_data=access_code)
    if wx_user_info is None:
        res.update(code=ResponseCode.WeChatAuthorizationFailure)
        return res.data

    # 验证微信用户信息本平台是否有，
    data = wx_login_or_register(wx_user_info=wx_user_info)
    if data is None:
        res.update(code=ResponseCode.Fail)
        return res.data
    res.update(data=data)
    return res.data


# --------------------测试手机短信验证码登陆注册-------------------------------#

@route(bp, '/testGetVerificationCode', methods=["GET"])
def test_get_verification_code():
    """
    获取手机验证码
    :return:
    """
    now = datetime.now()
    res = ResMsg()

    category = request.args.get("category", None)
    # category 参数如下：
    # authentication: 身份验证
    # login_confirmation: 登陆验证
    # login_exception: 登陆异常
    # user_registration: 用户注册
    # change_password: 修改密码
    # information_change: 信息修改

    phone = request.args.get('phone', None)

    # 验证手机号码正确性
    re_phone = PhoneTool.check_phone(phone)
    if phone is None or re_phone is None:
        res.update(code=ResponseCode.MobileNumberError)
        return res.data
    if category is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data

    try:
        # 获取手机验证码设置时间
        flag = Redis.hget(re_phone, 'expire_time')
        if flag is not None:
            flag = datetime.strptime(flag, '%Y-%m-%d %H:%M:%S')
            # 判断是否重复操作
            if (flag - now).total_seconds() < 60:
                res.update(code=ResponseCode.FrequentOperation)
                return res.data

        # 获取随机验证码
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        template_param = {"code": code}
        # 发送验证码
        sms = SendSms(phone=re_phone, category=category, template_param=template_param)
        sms.send_sms()
        # 将验证码存入redis，方便接下来的验证
        Redis.hset(re_phone, "code", code)
        # 设置重复操作屏障
        Redis.hset(re_phone, "expire_time", (now + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'))
        # 设置验证码过去时间
        Redis.expire(re_phone, 60 * 3)
        return res.data
    except Exception as e:
        logger.exception(e)
        res.update(code=ResponseCode.Fail)
        return res.data


@route(bp, '/testPhoneLoginOrRegister', methods=["POST"])
def test_phone_login_or_register():
    """
    用户验证码登录或注册
    :return:
    """
    res = ResMsg()

    obj = request.get_json(force=True)
    phone = obj.get('account', None)
    code = obj.get('code', None)
    if phone is None or code is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    # 验证手机号和验证码是否正确
    flag = PhoneTool.check_phone_code(phone, code)
    if not flag:
        res.update(code=ResponseCode.InvalidOrExpired)
        return res.data

    # 登陆或注册
    data = phone_login_or_register(phone)

    if data is None:
        res.update(code=ResponseCode.Fail)
        return res.data
    res.update(data=data)
    return res.data


# --------------------测试PDF报表输出-------------------------------#

@route(bp, '/testPDF', methods=["GET"])
def test_pdf():
    """
    测试pdf报表输出
    :return:
    """
    res = ResMsg()
    report_path = current_app.config.get("REPORT_PATH", "./report")
    file_name = "{}.pdf".format(uuid.uuid4().hex)
    path = os.path.join(report_path, file_name)
    path = pdf_write(path)
    path = path.lstrip(".")
    res.update(data=path)
    return res.data


# --------------------测试Celery-------------------------------#


@route(bp, '/testCeleryAdd', methods=["GET"])
def test_add():
    """
    测试相加
    :return:
    """
    result = add.delay(1, 2)
    return result.get(timeout=1)


@route(bp, '/testCeleryFlaskAppContext', methods=["GET"])
def test_flask_app_context():
    """
    测试获取flask上下文
    :return:
    """
    result = flask_app_context.delay()
    return result.get(timeout=1)
