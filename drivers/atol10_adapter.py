from drivers import libfptr101
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
from abc import ABC, abstractmethod
import random
import time

class CROperationError(Exception):
    def __init__(self, route, data):
        self.data = data
        self.route = route
        
class CRFatalError(Exception):
    def __init__(self, text):
        self.text = text

class Logger():
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance=logging.getLogger('main_log')
        return cls.instance

        
def cr_coro(method): #Декоратор для асинхронного использования методов работы с кассой
    async def wrapped(self, *args, **kwargs):
        async with self.lock:
            result=await self.loop.run_in_executor(None, method, self, *args, **kwargs)
        return result
    return wrapped  

class Cash_register_interface(ABC): #Интерфейс адаптера, через который осуществляется 
                                    #взаимодействие программы с драйвером кассы
    @cr_coro
    @abstractmethod 
    def register_operation(self, email, products, payments, total,
                           receiptType, operator=None, is_electronary=True, r1192=None):
        pass
    
    @cr_coro
    @abstractmethod 
    def close_shift(self):
        pass

    @cr_coro    
    @abstractmethod 
    def close(self):
        pass
    

  
class Atl_cash_register(Cash_register_interface):
    def __init__(self, cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_protocol, cr_passwd, 
                 shift_closing_delay=5, shift_duration=86400, auto_shift=True, loop=None ):
        #cr_model - модель кассы, cr_port - тип порта, cr_ofd_channel - канал для обмена с ОФД , cr_baudrate -скорость соединения
        #cr_protocol - версия протокола обмена драйвера с кассой , cr_passwd - пароль пользователя кассы
        #указанные выше параметры, их значения описаны на сайте производителя касс, также можно ориентироваться по 
        #исходному коду DTO, все переменные имеют понятные названия 
                
        #Параметры кассовой смены:
        #auto_shift - автоматическое управление сменой длительностью shift_duration (в секундах)
        #shift_closing_delay - на сколько раньше установленного времени начать процедуру окончания смены, данный параметр необходим,
        #чтобы гарантированно закрыть смену во время (если опоздать с закрытием смены, касса перестанет принимать 
        #регистрацию фискальных документов), значение по умолчинию - 5 с
        
                
        self.lock=asyncio.Lock()
        DTO_LIB='drivers/libfptr10.so'
        self.driver=libfptr101.IFptr(DTO_LIB)
        self._setSingleSetting('UserPassword', cr_passwd)
        self._setSingleSetting('LIBFPTR_SETTING_MODEL', cr_model)
        self._setSingleSetting('LIBFPTR_SETTING_PORT', cr_port)
        self._setSingleSetting('LIBFPTR_SETTING_OFD_CHANNEL', cr_ofd_channel)
        self._setSingleSetting('BaudRate', cr_baudrate)
        self._setSingleSetting('Protocol', cr_protocol)
        self.driver.applySingleSettings()
        self.driver.open()
        
        
        self.name='Atl_cash_register'
        self.shift_live_time=shift_duration
        self.shift_closing_delay=shift_closing_delay #задержка при закрытии смены по таймеру
        if not loop:
            loop=asyncio.get_event_loop() 
        self.loop=loop # 
        self.auto_shift=auto_shift
        if auto_shift:
            self.shift_closing_task=loop.create_task(self.shift_closing_timer())
        
        
    async def shift_closing_timer(self, seconds_to_close=None):
        if seconds_to_close is None:
            cr_state = await self.get_shift_state()   
            if cr_state['value']>=1:
                seconds_to_close=cr_state['now_dateTime']-cr_state['start_dateTime'].timestamp()-self.shift_live_time
                seconds_to_close=seconds_to_close-self.shift_closing_delay
            else:
                await asyncio.sleep(0)
                return
        await asyncio.sleep(seconds_to_close)
        await self.close_shift()
                      

    def _shift_closing_control(self, call_async=False):
        cr_state = self.get_shift_state()
        cr_nowDateTime = self._get_time().timestamp()
        if cr_state['value']>=1:
            seconds_to_close=cr_state['now_dateTime']-cr_state['start_dateTime'].timestamp()-self.shift_live_time
            return seconds_to_close



    @property
    def shift_opened(self):
        return self._shift_opened    

    @cr_coro
    def close_shift(self, delay=0):
        time.sleep(delay)
        self._close_shift       
           
    def _close_shift(self):
        self._setParam('LIBFPTR_PARAM_REPORT_TYPE', 'LIBFPTR_RT_CLOSE_SHIFT')
        #self._setParam('LIBFPTR_PARAM_REPORT_ELECTRONICALLY', True) #чтобы не печатался отчет о закрытии смены
        self.driver.report()
        counter=0
        while self.driver.checkDocumentClosed() < 0:  # проверка закрыт ли документ      
             time.sleep(0.5)
             counter+=1
             if counter>=10:
                  raise CRFatalError('Невозможно закрыть смену')
        self._shift_opened=False 
       

    @cr_coro 
    def get_shift_state(self): #состояние смены
        return self._get_shift_state()
    
    def _get_shift_state(self):
        data={}
        self._setParam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_SHIFT_STATE')
        self._queryData()
        data['value'] = self._getParamInt('LIBFPTR_PARAM_SHIFT_STATE') # 0 - смена закрыта, 1 - открыта, 2 - время смены истекло
        data['number'] = self._getParamInt('LIBFPTR_PARAM_SHIFT_NUMBER')
        # Тип переменной datetime - datetime.datetime
        data['start_dateTime'] = self._getParamDateTime('LIBFPTR_PARAM_DATE_TIME')
        data['now_dateTime'] = self._get_time()
        return data
   
    @cr_coro
    def get_time(self):
        return self._get_time()

    def _get_time(self): #текущее время в кассе
        self._setParam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_DATE_TIME')
        self._queryData()
        cr_dateTime = self._getParamDateTime('LIBFPTR_PARAM_DATE_TIME')
        return cr_dateTime    

     
    def _get_const(self, param):
        return getattr(self.driver, param)    
    
    def _getParamInt(self, param):
        if isinstance(param, str):
           param=self._get_const(param)
           return self.driver.getParamInt(param)
           
    def _getParamDouble(self, param):
        if isinstance(param, str):
           param=self._get_const(param)
           return self.driver.getParamDouble(param)

    def _getParamString(self, param):
        if isinstance(param, str):
           param=self._get_const(param)
           return self.driver.getParamString(param)

    def _getParamDateTime(self, param):
        if isinstance(param, str):
           param=self._get_const(param)
           return self.driver.getParamDateTime(param)           

   
    def _setSingleSetting(self, param, value):
        if isinstance(param, str):
           param=self._get_const(param) if param[:8]=='LIBFPTR_' else param
        if isinstance(value, str):
           value=self._get_const(value) if value[:8]=='LIBFPTR_' else value
        self.driver.setSingleSetting(str(param), str(value))   
       
    def _setParam(self, param, value):
        if isinstance(param, str):
           param=self._get_const(param)
        if isinstance(value, str):
           value=self._get_const(value) if value[:8]=='LIBFPTR_' else value
        self.driver.setParam(param, value)  
    
    def _openReceipt(self):
        return self.driver.openReceipt()
    
    def _errorDescription(self):
        return self.driver.errorDescription
    
    def _sort_by_payment_type(self, item):
        return 10-int(item['payment_type'])
     
    def _register_payments(self, payments):
        payments.sort(payments, key=_sort_by_payment_type)
        for payment in payments:
            self._setParam('LIBFPTR_PARAM_PAYMENT_TYPE', payment['payment_type'])
            self._setParam('LIBFPTR_PARAM_PAYMENT_SUM', float(payment['summ']))
            if self.driver.payment()<0:
                self._cancel_receipt()
                raise CROperationError(self.name, 'Ошибка регистрации оплаты: ' + self._errorDescription())
        # Тип оплаты
        # 0 - наличными
        # 1 - безналичными
        # 2 - предварительная оплата (аванс)
        # 3 - последующая оплата (кредит)

    def _register_products(self, products):
        for product in products:
            self._setParam('LIBFPTR_PARAM_COMMODITY_NAME', product['name'])
            self._setParam('LIBFPTR_PARAM_PRICE', float(product['price']))
            self._setParam('LIBFPTR_PARAM_QUANTITY', int(product['quantity']))
            self._setParam('LIBFPTR_PARAM_TAX_TYPE', 'LIBFPTR_TAX_NO') #налог. Если организация платит НДС, то необходимо изменить с этим учетом
            self._setParam(1212,int(product['paymentObject']))
            if self.driver.registration()<0:
                self._cancel_receipt()
                raise CROperationError(self.name, 'Ошибка регистрации товара: ' + self._errorDescription()) 
              
    def _queryData(self):
        self.driver.queryData()    
 
    def _fnQueryData(self):
        self.driver.fnQueryData() 
    
    def _set_operator(self, operator): #при оффлайн продаже необходимо указать оператора
        self._setParam(1021, name)
        self._setParam(1203, inn)
        self.driver.operatorLogin()

    @cr_coro
    def cancel_receipt(self):
        self._cancelReceipt()   
        
    def _cancel_receipt(self):
        self.driver.cancelReceipt()  

    @cr_coro
    def get_not_sent_docs(self):
        self._setParam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_OFD_EXCHANGE_STATUS')
        self._fnQueryData()
        data={}
        data['unsentCount'] = self._getParamInt('LIBFPTR_PARAM_DOCUMENTS_COUNT')
        data['unsentFirstNumber'] = self._getParamInt('LIBFPTR_PARAM_DOCUMENT_NUMBER')
        data['unsentDateTime'] = self._getParamDateTime('LIBFPTR_PARAM_DATE_TIME')
        return data    

    @cr_coro
    def print_ofd_connection_report(self):
        self._setParam('LIBFPTR_PARAM_REPORT_TYPE', 'LIBFPTR_RT_OFD_TEST')
        self.driver.report()
        
    @cr_coro    
    def show_ofd_connection_report(self, command):
        result=command.result
        self._setParam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_OFD_EXCHANGE_STATUS')
        self._fnQueryData()
        result['exchangeStatus'] = self._getParamInt('LIBFPTR_PARAM_OFD_EXCHANGE_STATUS')
        result['unsentCount'] = self._getParamInt('LIBFPTR_PARAM_DOCUMENTS_COUNT')
        result['firstUnsentNumber']   = self._getParamInt('LIBFPTR_PARAM_DOCUMENT_NUMBER')
        result['ofdMessageRead'] = self._getParamBool('LIBFPTR_PARAM_OFD_MESSAGE_READ')
        result['dateTime'] = self.getParamDateTime('LIBFPTR_PARAM_DATE_TIME')
        return result
    
   
    @cr_coro
    def register_operation(self, email, products, payments, total, receiptType, operator=None, 
        is_electronary=True, r1192=None, test_mode=False):
        #регистрация фискальной операции
        allowed_receiptTypes={1:'LIBFPTR_RT_SELL', 2:'LIBFPTR_RT_SELL_RETURN', 7:'LIBFPTR_RT_SELL_CORRECTION',
                              8:'LIBFPTR_RT_SELL_RETURN_CORRECTION', 4:'LIBFPTR_RT_BUY', 5:'LIBFPTR_RT_BUY_RETURN',
                              9:'LIBFPTR_RT_BUY_CORRECTION', 10:'LIBFPTR_RT_BUY_RETURN_CORRECTION'} 
        #LIBFPTR_RT_SELL - чек прихода
        #LIBFPTR_RT_SELL_RETURN - чек возврата прихода
        #LIBFPTR_RT_SELL_CORRECTION - чек коррекции прихода
        #LIBFPTR_RT_BUY - чек расхода
        #LIBFPTR_RT_BUY_RETURN - чек возврата расхода
        #LIBFPTR_RT_BUY_CORRECTION - чек коррекции расхода                     
                              
        #При регистрации возвратов и коррекции ошибок в чеках, можно руководствоваться материалами https://www.nalog.ru/rn27/news/smi/7746012/
        #http://consultantkhv.ru/newspaper/ispravlenie-oshibok-dopushhennyx-pri-formirovanii-kassovyx-chekov/                      
    
        receiptType=allowed_receiptTypes[int(receiptType)]
        if self._checkDocumentClosed()<0:
             self.cancel_receipt()
             if self._checkDocumentClosed()<0:
                  raise CROperationError(self.name, 'Предыдущий документ не закрыт')
       
        if not is_electronary: #чек электронный или бумажный
            self._set_operator(operator)
            self._setParam('LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY', False)
        else:
            self._setParam('LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY', True)

        self._setParam('LIBFPTR_PARAM_RECEIPT_TYPE', 'LIBFPTR_RT_SELL')
        self._setParam(1008, command.email.value)
       
       #дополнительный реквизит 1192 рекомендуется использовать в операциях исправления ошибок:
       #возвраты, коррекции, "повторные чеки", в нем указывается ФПД исправляемого (первоначального) чека,
       #ссылка с подробной информацией о возвратах и коррекциях выше
        if r1192: 
             self._setParam(1192, r1192)
       
        if self._openReceipt()<0:
             self.driver.cancelReceipt() 
             raise CROperationError(self.name, 'Ошибка открытия чека: ' + self._errorDescription())
              
        self._register_products(products)
        self._register_payments(payments)
        
        #(Налоги - НДС)
        self._setParam('LIBFPTR_PARAM_TAX_TYPE', 'LIBFPTR_TAX_NO')
        self._setParam('LIBFPTR_PARAM_TAX_SUM', 0)  # Если организация платит НДС, необходимо учесть это и включить налог во входные данные
        self._receiptTax()
        #регистрируем итог
        self._setParam('LIBFPTR_PARAM_SUM', float(total))

        if self.driver.receiptTotal()<0:
             self.driver.cancelReceipt()
             raise CROperationError(self.name, 'Ошибка регистрации общей суммы чека: ' +self._errorDescription())
              

        if test_mode:
        #Если тестовый режим, то откатываем документ
             return self.driver.cancelReceipt()

        #закрываем чек        
        if self.driver.closeReceipt()<0:
             self.driver.cancelReceipt()
             raise CROperationError(self.name, 'Ошибка закрытия чека: ' +self._errorDescription())
             
        self._setParam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_LAST_RECEIPT')
        self._fnQueryData()
        result_data={}
        result_data['fnSerialNumber'] = self._getParamInt('LIBFPTR_PARAM_SERIAL_NUMBER')
        result_data['documentNumber'] = self._getParamInt('LIBFPTR_PARAM_DOCUMENT_NUMBER')
        result_data['receiptType']    = self._getParamInt('LIBFPTR_PARAM_RECEIPT_TYPE')
        result_data['receiptSum']     = self._getParamDouble('LIBFPTR_PARAM_RECEIPT_SUM')
        result_data['fiscalSign']     = self._getParamString('LIBFPTR_PARAM_FISCAL_SIGN')
        result_data['dateTime']       = self._getParamDateTime('LIBFPTR_PARAM_DATE_TIME')
        
        closing_task = getattr(self, 'shift_closing_task', None)
        if closing_task and (closing_task.done() ^ closing_task.cancelled()):
            self.closing_task=loop.create_task(shift_closing_timer())

        return result_data

    @cr_coro
    def close(self):
        self.driver.close()
