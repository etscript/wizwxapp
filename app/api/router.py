from app.api.api_test import bp as bp_api_test
from app.api.services import ArticleAPI
from app.api.tianyancha import bp as tianyancha
from app.api.wxusers import bp as wxusers
from app.api.company_items import bp as company_items

router = [
    bp_api_test,  # 接口测试
    ArticleAPI,  # 自定义MethodView
    wxusers,
    tianyancha,
    company_items,
]
