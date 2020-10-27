from aiohttp.web import View, HTTPNotFound, json_response, HTTPBadRequest
import datetime
from typing import Generator
import json
from core.events import AbstractEventDispatcher
from receipt.events import ReceiptCreated
from receipt.serializers import ReceiptSerializer
from receipt.services import AbstractReceiptProcessingService, AbstractReceiptCreationService
from receipt.receipt_read import ReceiptNotExists
from .facades import AbstractFiscalServiceGroupFacade


class ServiceGroupNotExists(Exception):
    pass


class ReceiptRegisterServiceView(View):
    @property
    def event_dispatcher(self) -> AbstractEventDispatcher:
        return self.request.app['event_dispatcher']

    @property
    def receipt_creation_service(self) -> AbstractReceiptCreationService:
        return self.request.app['receipt_creation_service']

    @property
    def receipt_id_generator(self) -> Generator:
        return self.request.app['receipt_id_generator']

    @property
    def receipt_processing_service(self) -> AbstractReceiptProcessingService:
        return self.request.app['receipt_processing_service']

    async def post(self):
        try:
            service_group_id = self.request.match_info['service_group_id']
        except KeyError:
            raise HTTPNotFound
        if self.receipt_processing_service.is_service_provided(service_group_id):
            raise HTTPNotFound
        deserializer = ReceiptSerializer.from_json(await self.request.json())
        if not deserializer.validate():
            return json_response(data={'errors': deserializer.errors}, status=400)
        user = self.request['user']
        try:
            # Receipt Data must be validated with domain logic. If data is not valid ValueError exception must be raised
            receipt = self.receipt_creation_service.create_receipt(user.id, int(service_group_id), deserializer.data)
        except ValueError as e:
            return json_response(data={'errors': str(e)}, status=400)
        receipt.id = next(self.receipt_id_generator)
        await self.event_dispatcher.handle(ReceiptCreated(receipt))
        await self.receipt_processing_service.proccess(receipt)
        receipt_view_location = '{}{}'.format(self.request.url, receipt.id)
        return json_response({'receipt_id': receipt.id, 'location': receipt_view_location})


class ReceiptReadServiceView:
    @staticmethod
    def _get_service_group_facade(request) -> AbstractFiscalServiceGroupFacade:
        return request.app['fiscal_service_group_facade']

    async def _is_reading_available(self, request, service_group_id):
        fiscal_service_facade = self._get_service_group_facade(request)
        try:
            service_group = await fiscal_service_facade.get_service_group(int(service_group_id))
        except ServiceGroupNotExists:
            return False
        if not service_group.is_enabled:
            return False
        return True

    @staticmethod
    def _get_receipt_repository(request):
        return request.config_dict['receipt_read_repository']

    @staticmethod
    def _get_service_group_id(request):
        return request.match_info['service_group_id']

    async def get_receipt(self, request):
        service_group_id = int(self._get_service_group_id(request))
        if not await self._is_reading_available(request, service_group_id):
            raise HTTPNotFound

        try:
            receipt_id = int(request.match_info['receipt_id'])
        except (ValueError, KeyError):
            raise HTTPBadRequest

        repository = self._get_receipt_repository(request)

        try:
            receipt_data = await repository.get(receipt_id, service_group_id)
        except ReceiptNotExists:
            raise HTTPNotFound
        return json_response(text=json.dumps(receipt_data, default=str))

    async def get_receipts(self, request):
        date_start = request.query.get('date_start', 0)
        date_end = request.query.get('date_end', 0)
        order_id = request.query.get('order_id', None)
        if not (date_start and bool(date_start)*bool(date_end)):
            raise HTTPBadRequest
        try:
            date_start = datetime.datetime.strptime(date_start, '%Y%m%d').date()
            date_end = datetime.datetime.strptime(date_end, '%Y%m%d').date()
        except ValueError:
            raise HTTPBadRequest
        if date_start < date_end:
            raise HTTPBadRequest
        repository = self._get_receipt_repository(request)
        service_id = self._get_service_group_id(request)
        if order_id:
            receipts = await repository.get_by_order_id(service_id, order_id)
            receipts = list(filter(lambda item: date_end <= item['registration_datetime'].date <= date_start, receipts))
        else:
            receipts = await repository.get_by_period(service_id, date_start, date_end)
        return json_response(text=json.dumps(receipts, default=str))













