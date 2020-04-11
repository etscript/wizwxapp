from datetime import datetime
from app.utils.core import db
from flask import current_app
import jwt

class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'user'
    id          = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name    = db.Column(db.String(128), nullable=False, server_default="")
    age    = db.Column(db.String(128), nullable=False, server_default="")


class UserLoginMethod(db.Model):
    """
    用户登陆验证表
    """
    __tablename__ = 'user_login_method'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)  # 用户登陆方式主键ID
    # user_id = db.Column(db.Integer, nullable=False)  # 用户主键ID
    login_method = db.Column(db.String(36), nullable=False)  # 用户登陆方式，WX微信，P手机
    identification = db.Column(db.String(36), nullable=False)  # 用户登陆标识，微信ID或手机号
    access_code = db.Column(db.String(36), nullable=True)  # 用户登陆通行码，密码或token
    nickname    = db.Column(db.String(128), nullable=True, server_default="")
    sex         = db.Column(db.String(1), nullable=False, server_default="0")
    admin       = db.Column(db.String(1), nullable=False, server_default="0")

    def to_dict(self):
        return {
            'id': self.id,
            'login_method': self.login_method,
            'identification': self.identification,
            'access_code': self.access_code,
            'nickname': self.nickname,
            'sex': self.sex,
            'admin': self.admin
        }

class Article(db.Model):
    """
    文章表
    """
    __tablename__ = 'article'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    title = db.Column(db.String(20), nullable=False)  # 文章标题
    body = db.Column(db.String(255), nullable=False)  # 文章内容
    last_change_time = db.Column(db.DateTime, nullable=False, default=datetime.now)  # 最后一次修改日期
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 作者


class ChangeLogs(db.Model):
    """
    修改日志
    """
    __tablename__ = 'change_logs'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 作者
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))  # 文章
    modify_content = db.Column(db.String(255), nullable=False)  # 修改内容
    create_time = db.Column(db.DateTime, nullable=False)  # 创建日期

class WXUser(db.Model):
    # 设置数据库表名
    __tablename__ = 'wxuser'
    id = db.Column(db.Integer, autoincrement=True)
    nickname = db.Column(db.String(128))
    openid = db.Column(db.String(255), primary_key=True)
    gender = db.Column(db.String(64))  
    country = db.Column(db.String(128))
    province = db.Column(db.String(128))
    city = db.Column(db.String(128))

    def to_dict(self):
        data = {
            'id': self.id,
            'nickname': self.nickname,
            'openid': self.openid,
            'gender': self.gender,
            'country': self.country,
            'province': self.province,
            'city': self.city
        }
        return data

    def from_dict(self, data):
        for field in ['nickname', 'openid', 'gender', 'country', 'province', 'city']:
            if field in data:
                setattr(self, field, data[field])
        self.openid = data["openId"]
        self.nickname = data["nickName"]

    def get_jwt(self, expires_in=3600):
        '''用户登录后，发放有效的 JWT'''
        payload = {
            "iss": 'wxapp',
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400 * 7,
            "aud": 'flask',
            "openid": self.openid,
            "nickname": self.nickname,
            "scopes": ['open']
        }
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256')
    
    @staticmethod
    def verify_jwt(token):
        '''验证 JWT 的有效性'''
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256'],
                audience="flask")
        except (jwt.exceptions.ExpiredSignatureError,
                jwt.exceptions.InvalidSignatureError,
                jwt.exceptions.DecodeError) as e:
            # Token过期，或被人修改，那么签名验证也会失败
            return None
        return WXUser.query.get(payload.get('openid'))


class Order(db.Model):
    # 设置数据库表名
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status = db.Column(db.String(128))
    company = db.Column(db.String(255))
    create = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    start = db.Column(db.DateTime, index=True)
    complete = db.Column(db.DateTime, index=True)
    price = db.Column(db.Float)
    email = db.Column(db.String(128))
    wxuser_openid = db.Column(db.String(255), db.ForeignKey('wxuser.openid'))  # 属于哪个用户
    code = db.Column(db.String(255))

    def to_dict(self):
        data = {
            'id': self.id,
            'status': self.status,
            'company': self.company,
            'create': self.create,
            'start': self.start,
            'complete': self.complete,
            'price': self.price,
            'email': self.email,
            'code': self.code
        }
        return data

    def from_dict(self, data):
        for field in ['status', 'company', 'price', 'email', 'code', 'wxuser_openid']:
            if field in data:
                setattr(self, field, data[field])

    @staticmethod
    def to_collection_dict(query, page=1, per_page=10, **kwargs):
        # 如果当前没有任何资源时，或者前端请求的 page 越界时，都会抛出 404 错误
        # 由 @bp.app_errorhandler(404) 自动处理，即响应 JSON 数据：{ error: "Not Found" }
        # resources = query.paginate(page, per_page)
        return [item.to_dict() for item in query]
