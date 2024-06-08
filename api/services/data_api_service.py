from extensions.ext_database import db
from models.data_api import DataAPI, DataAPIApplication, DataAPICall
from datetime import datetime


class DataAPIService:

    @classmethod
    def get_all_apis(cls, tenant_id, page=1, limit=10, name=None, price_min=None, price_max=None,
                     authorization_method=None, status=None):
        query = DataAPI.query

        # 使用条件来筛选
        if name:
            query = query.filter(DataAPI.name.ilike(f"%{name}%"))

        if price_min is not None:
            query = query.filter(DataAPI.price_per_call >= price_min)

        if price_max is not None:
            query = query.filter(DataAPI.price_per_call <= price_max)

        if authorization_method:
            query = query.filter(DataAPI.authorization_method == authorization_method)

        # 获取带筛选状态的API的信息总数
        all_apis = query.all()

        # 获取每个API对应的申请状态
        application_dict = {
            application.data_api_id: application.status
            for application in DataAPIApplication.query.filter_by(tenant_id=tenant_id).all()
        }

        if status != 'all':
            if status == 'not_applied':
                all_apis = [api for api in all_apis if api.id not in application_dict]
            else:
                all_apis = [api for api in all_apis if application_dict.get(api.id) == status]

        total_apis = len(all_apis)

        # 分页
        paginated_apis = all_apis[(page - 1) * limit: page * limit]

        api_list = []
        for api in paginated_apis:
            api_dict = {
                'id': api.id,
                'name': api.name,
                'image_url': api.image_url,
                'price_per_call': api.price_per_call,
                'authorization_method': api.authorization_method,
                'status': application_dict.get(api.id, 'not_applied')
            }
            api_list.append(api_dict)

        result = {
            'total': total_apis,
            'page': page,
            'limit': limit,
            'apis': api_list
        }

        return result

    @classmethod
    def apply_for_api(cls, tenant_id, api_id):
        api = DataAPI.query.get(api_id)
        if not api:
            raise Exception("Data API not found")

        application = DataAPIApplication.query.filter_by(tenant_id=tenant_id, data_api_id=api_id).first()
        if application:
            raise Exception("Already applied for this API")

        status = 'approved' if api.authorization_method == 'auto' else 'pending'
        approved_at = datetime.utcnow() if status == 'approved' else None

        application = DataAPIApplication(
            tenant_id=tenant_id,
            data_api_id=api_id,
            status=status,
            applied_at=datetime.utcnow(),
            approved_at=approved_at
        )
        db.session.add(application)
        db.session.commit()

        return application

    @classmethod
    def call_api(cls, tenant_id, api_id):
        application = DataAPIApplication.query.filter_by(tenant_id=tenant_id, data_api_id=api_id,
                                                         status='approved').first()
        if not application:
            raise Exception("API not authorized")

        api = DataAPI.query.get(api_id)
        if not api:
            raise Exception("Data API not found")

        call = DataAPICall(
            tenant_id=tenant_id,
            data_api_id=api.id,
            called_at=datetime.utcnow(),
            billing_amount=api.price_per_call
        )
        db.session.add(call)
        db.session.commit()

        return call
