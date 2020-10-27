Online fiscal cash register server v 0.2 (beta).

The application provides REST API for receipt registrations, storing receipt information and a dash board for managing
cash register hardware and an access control system.

Installation

Install all dependencies mentioned in requirements.txt

Set the host name and the configuration name in the settings.py module.
The 'test' configuration is set as a default configuration, it uses in memory data storages, therefore use it only for tests.


Run the server python -m cr_server. Follow '{your_host_name}/admin/' web page and login with superuser credentials
(login: admin, password: admin for the test configuration for default).
To add a new user follow the 'Пользователи' (Users) link. Press the 'Добавить' (Add) button.
In a appeared modal window set user's settings and click the button 'Сохранить' (Save).
The new user will be created and appear in a users list. 

Managing fiscal cash register service groups

A cash register is used for a receipt registration. Along with the receipt registration we usually need storing and reading
receipt data, managing a cash register shift, printing reports and so on. Services responsible for executing this tasks
are grouped in service groups. Each of the service groups contains a receipt registration service, a receipt reading service,
the service group has a fiscal cash register device connected and defines an access policy for users allowed to use
the services of the group.

To add the a new service group follow the link 'Кассовые сервисы' (Cash register services). 
Press the 'Добавить' (Add) button. 
In an appeared modal window choose a cash register model and set its configuration parameters, and click the button
'Сохранить' (Save).
The new item in a service group list will appear.
Then click the link 'Настройки доступа' (Access settings) in the service group block. In an appeared modal window
use arrow buttons in the center to allow or disallow access for users.
The users that have permission for an access to the fiscal service group must be moved at a right list.
To run the cash register device press 'Пуск' (Start) button.

REST API 

The REST API use basic authorization. The authorization header contains the word Basic word followed by a space and
a base64-encoded string username:password. Example: Authorization: Basic ZGVtbzpwQDU1dzByZA==

Receipt registraion service
 
End point:
{your_host_name}/service_groups/{service_group_id}/receipts/

To register a receipt the client makes a JSON POST HTTP request as in the example bellow:

{'email': 'example@mail.ru',
 products': [{'name': 'Grain crusher', 'payment_state_int': 1, 'price': 100, 'commodity_type_int': 1, 'quantity': 1.0},
                 {'name': 'Shipping', 'payment_state_int': 1, 'commodity_type_int': 4, price': 100, 'quantity': 1.0}],
                  receiptType': 1, 'payments': [{'payment_type_int': 1, 'payment_sum': 200}]}
				  
			  
If the request processed successfully the server sends HTTP responce with the status code 200 and a json object:
{'id': '10', 'location':{your_host_name}/service_groups/{service_group_id}/receipts/10'}
This means the receipt is in process, the receipt id is 10 and the receipt resource URL is given.

Receipt registration parameters:

order_id : order id,  type int, is not required 
mistaken_receipt_number:  a number of the receipt we are going to correct, you should use this parameter
                          when you need to correct some receipt registered in the past, type str.
                          This parameter is required only for correction on cash registers using FFD version 1.05
email: customers email, type str, is required if a receipt does not contain phone_number data 
phone_number: customers phone_number, type str, is required if a receipt does not contain email data
tax_system: type int, the possible values: OSN - 1, USN6 - 2, USN15 - 4, ENVD - 8, ESN - 16, Patent - 32, is required
correction_reason - a correction reason, type string, is required only in correcting receipts
correction_date: a correction date,  type string, format: dd:mm:yyyy, is required only in correcting receipts
doc_number: a correction document number, type string, is required only in correcting receipts
precept: type boolean, is required only in correcting receipts
need_print: boolean, to print or not to print the receipt
receiptType: a receipt type, type: int, the possible values: sell receipt - 1, sell refund receipt - 2,
             sell correcting receipt - 7, sell refund correcting receipt - 8, purchase receipt - 4,
             purchase refund receipt - 5, purchase correcting receipt - 9, purchase  refund correcting receipt - 10

products: the list of products (commodities), is required, product dict description:
         {'name':  string, is required
          'payment_state_int': int, possible values: full prepayment - 1, prepayment - 2, advance - 3, full payment - 4,
                              is required
          'price': int or decimal, is required
          'commodity_type_int': int, possible values: Product - 1, Service - 4, is required
          'quantity': int or decimal, is required}
payments: the list of payments, is required, payment dict description:
          {'payment_type_int': 1, possible values: Cash - 0, Card - 1, Prepayment - 2, is required
          'payment_sum': int or decimal, is required, }


Receipt reading service

To get a receipt the client makes a GET HTTP request to the receipt resource:

{your_host_name}/service_groups/{service_group_id}/receipts/{receipt_id}'}

The example of a responce:

{'id': 1,
  'order_id': None, 
  'user_id': 1, 
  'service_id': 2, 
  'mistaken_receipt_number': 'None', 
  'email': 'dvil@mail.ru', 
  'phone_number': 'None', 
  'registrator_id': 1, 
  'fiscal_sign': '89198483', 
  'registration_datetime': '2020-10-22 14:43:50.199065', 
  'cashier': None, 
  'shift_num': 11, 
  'tax_system': None, 
  'correction_data': None, 
  'receipt_in_shift_num': 1, 
  'need_print': False, 
  'receipt_num': None, 
  'payments_total': '200.00', 
  'commodities_total_cost': '200.00', 
  'commodities': [{'name': 'Поилка ниппельная', 'quantity': '1', 'price': '100.00', 'commodity_type_int': 1, 'payment_state_int': 1, 'quantity_prec': 0, 'quantity_unit': None, 'tax_type_int': 6}, 
                        {'name': 'Организация доставки товара', 'quantity': '1', 'price': '100.00', 'commodity_type_int': 4, 'payment_state_int': 1, 'quantity_prec': 0, 'quantity_unit': None, 'tax_type_int': 6}], 
  'payments': [{'paymetn_sum': '200.00', 'payment_type_int': 1}], 
  'state': 'success', 
  'registration_number': '002353466533', 
  'registrator_serial': '2356547774453454', 
  'fn_serial': '0023423423', 'ffd_version': '105', 
  'ofd_name': 'ООО "ОФД"', 
  'ffd_inn': '34567789999', 
  'company_name': 'ИП Иванов Иван Иванович', 
  'company_inn': '664353523234', 
  'operations_address': 'Ленина 55, Москва', 
  operations_place': 'http://www.sale.ru', 
  'cashier': None}




  




