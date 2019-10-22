from db import model
import json


class Operations(model.Model):
    operation_fields = ('fnSerialNumber', 'receiptType', 'receiptSum', 'fiscalSign', 'dateTime',
                        'order_id', 'summ', 'email')

    async def add_new_onperation(self, user_id, command, client_operation_id, client_operation_datetime, status,
                                 datetime_add, operation_data=None):
        params = (command, client_operation_id, user_id, status, client_operation_datetime,
                  datetime_add)
        request = '''INSERT INTO operation SET command=%s, client_operation_id=%s,
        user_id=%s, status=%s, client_operation_datetime=%s, datetime_add=%s'''
        operation_id = await self.db.query(request, params)
        if isinstance(operation_data, dict):
            # запись входных данных (сделано одтельной таблицей, потому что нужно хранить для отладки
            # и для исключительных ситуациий, со временем будут удаляться)
            data = operation_data.copy()
            dont_include_keys = ('user_id', 'command', 'client_operation_id', 'client_operation_datetime',)
            for key in dont_include_keys:
                data.pop(key, None)
            json_data = json.dumps(data)
            request = '''INSERT INTO `income_data` SET `operation_id`=%s, data=%s'''
            await self.db.query(request, (str(operation_id), json_data,))
        return operation_id

    async def add_result(self, operation_id, result=None, errors=None):
        # запись результата нефискальной операции и/или ошибок (ошибки фискальных операций тоже сюда пишутся)
        value_list = ["", ]
        request = "INSERT INTO `operation_result` (operation_id"
        if result:
            request += " , result_data"
            value_list.append("'" + json.dumps(result) + "'")
        if errors:
            request += " , errors"
            value_list.append("'" + json.dumps(errors) + "'")
        request += ") VALUES (" + operation_id + ", ".join(value_list) + ")"

    async def add_fiscal_document(self, operation_id, documentType, documentNumber,
                                  receiptType, fiscalSign, fnSerialNumber, documentDate,
                                  document_summ):
        # запись результата фискальной операции

        values = (operation_id, documentType, documentNumber, receiptType, fiscalSign,
                  fnSerialNumber, documentDate, document_summ,)

        request = '''INSERT INTO `fiscal_document` (operation_id, documentType, 
        documentNumber, receiptType, fiscalSign, fnSerialNumber, documentDate, document_summ) VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s)'''
        fd_id = await self.db.query(request, values)
        return fd_id

    async def update_status(self, com_id,
                            status):  # статусы: 0 - добавленный (в процессе), 1- операция выполнена, 2 - обработан, но есть предостережения (ошибки), 3 - завершено с ошибкой (не выполнено)
        request = "UPDATE `operation` SET `status`= %s WHERE `id`= %s"
        await self.db.query(request, (status, com_id,))

    async def get_proccessed_operation_id(self, user_id, client_operation_id, client_operation_datetime):
        request = '''SELECT id FROM operation WHERE user_id=%s AND client_operation_id=%s
        AND client_operation_datetime=%s'''
        operation_id = await self.db.query(request, (user_id, client_operation_id, client_operation_datetime, ))
        return operation_id

    async def get_operation_by_id(self, com_id, user_id, full_data=False):
        addition = ''
        if full_data:
            addition = ', client_operation_id, client_operation_datetime, user_id'
        request = '''SELECT id, command, status, datetime_add{} FROM operation 
                   WHERE id=%s AND user_id=%s'''.format(addition)
        result = await self.db.query(request, (com_id, user_id,))
        return result

    async def get_operation(self, user_id, client_operation_id, payment_datetime):
        request = "SELECT * FROM `operations` WHERE `user_id`=%s AND `client_operation_id`=%s AND `payment_datetime`=%s"
        result = await self.db.query(request, (user_id, client_operation_id, payment_datetime,))
        return result

    async def get_results(self, operation_id, get_errors=False):
        request = "SELECT result_data AS result"
        if get_errors:
            request += ", errors "
        request += "FROM operation_result WHERE operation_id=%s"
        result = await self.db.query(request, (operation_id,))
        for key in result:
            result['key'] = json.loads(result['key'])
        return result

    async def get_fiscal_operation_results(self, operation_id, get_errors=False):
        request = '''SELECT fd.documentType, fd.documentNumber, fd.receiptType, fd.fiscalSign, 
        fd.fnSerialNumber, fd.documentDate, fd.document_summ'''
        if get_errors:
            request += ", ors.errors FROM fiscal_document AS fd LEFT JOIN operation_result AS ors ON (ors.operation_id=fd.operation_id)"
        else:
            request += " FROM fiscal_document AS fd"
        request += " WHERE fd.operation_id=%s"
        result = await self.db.query(request, (operation_id,))
        return result
