from aiohttp import web
from .views import ReceiptRegisterServiceView, ReceiptReadServiceView


def get_routes():
    receipt_read_view = ReceiptReadServiceView()
    return [web.view('/{service_group_id}/receipts/', ReceiptRegisterServiceView,
                      name='receipt_register'),
            web.get('/{service_group_id}/receipts/{receipt_id}', receipt_read_view.get_receipt,
                    name='receipt_get'),
            ]

