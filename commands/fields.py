import re
from decimal import Decimal
from decimal import InvalidOperation

#Исключения
class ValidationError(Exception):
    def __init__(self, route, data):
        self.data = data
        self.route = route
          

class Field():
    #Родитель всех полей команд
    def __init__(self, required=True, default=None):
        self.required=required
        self.default=default  #значение по умолчанию
        self._name=''  #имя поля по умолчанию


    def __set_name__(self, owner, name):
        self._name = name

    def validate(self, data, route, main_parent):
        #Валидация с нормализацией данных вызывает базовый и конкретный тип обработки
        #возвращает нормализованные данные
        route=self.get_route(route)
        new_data=self.base_validation(data, route, main_parent)
        new_data=self.current_validation(new_data, route, main_parent)

        return new_data

    def base_validation(self, data, route, main_parent):
        new_data=data
        return new_data
    
    def current_validation(self, data, route, main_parent):
        new_data=data
        return new_data
   
    def get_name(self):
        self._name=getattr(self, '_name', '')
        return self._name    

    def get_route(self, route=None):
    #Маршрут до конкретного поля команды (используется для отображения
    #вложенности полей команды, в частности при возникновении ошибки валидации)
         route=(route+'->') if route else ''
         return route+self.get_name()


            
class Single_field(Field):
    def __init__(self, allowed_values=None, required=True, default=None):
        super().__init__(required, default)
        if allowed_values:
            self.allowed_values = set() 
            for val in allowed_values:
                val=self.current_validation(val, '', None)
                self.allowed_values.add(val)
        else:
            self.allowed_values=None
            
            
    #Родитель для полей с элементарными типами данных
    def base_validation(self, value, route, command_instance=None):
        if value is None:
            if self.required:
                raise ValidationError(route, 'Отсутствует обязательное поле')
            else: 
                return self.default
        if self.allowed_values and value not in self.allowed_values:
            raise ValidationError(route, 'Неразрешенное значение поля')

        return value

class Numeric_field(Single_field):
    def __init__(self, min_value=0, max_value=None, allowed_values=None, required=True, default=None):
        self.min_value=min_value
        self.max_value=max_value
        super().__init__(allowed_values=allowed_values, required=required, default=default)

    def is_in_range(self, value, route):
        if self.min_value is not None and value<self.min_value:
            raise ValidationError(route, 'Значение поля не должно быть меньше {}'.format(self.min_value))
        if self.max_value is not None and value>self.max_value:
            raise ValidationError(route, 'Значение поля не должно быть больше {}'.format(self.max_value))
        return value


class Integer_field(Numeric_field):
    def current_validation(self, value, route, main_parent):
        try:
            value=int(value)
        except (ValueError, TypeError): 
            raise ValidationError(route, 'Неверный тип поля, должно быть целым числом')
        value=self.is_in_range(value, route)
        return value
            
         
            
class Decimal_field(Numeric_field):
    def __init__(self, min_value=0, max_value=None, precision=2, allowed_values=None, required=True, default=None):
        super().__init__(min_value, max_value, allowed_values=allowed_values, required=required, default=default)
        self._precision='.{}'.format('0'*precision) #точность (количество знаков после запятой)

    @property
    def precision(self):
        return len(self._precision-1)

    def current_validation(self, value, route, main_parent):
        try:
            value=Decimal(value).quantize(Decimal(self._precision))
        except (ValueError, TypeError, InvalidOperation):
            raise ValidationError(route, 'Неверный тип поля, должно быть целым или десятичной дробью')
        value=self.is_in_range(value, route)
        return value



        
class String_field(Field):
    def __init__(self, *a, min_lenght=1, max_lenght=None, **k):
        self.min_lenght=min_lenght
        self.max_lenght=max_lenght
        super().__init__(*a,**k)

    def check_lenght(self, value, route):
        lenght=len(value)
        if self.min_lenght and lenght<self.min_lenght:
            raise ValidationError(route, 'Количество симовлов в строке не должно быть меньше {}'.format(self.min_lenght))
        if self.max_lenght and lenght>self.max_lenght:
            raise ValidationError(route, 'Количество симовлов в строке не должно быть больше {}'.format(self.max_lenght))
        return value

    def current_validation(self, value, route, main_parent):
        try:
            value=str(value)
        except (ValueError, TypeError): 
            raise ValidationError(route, 'Неверный тип поля, должно быть строковой переменной')
        value=self.check_lenght(value, route)
        return str(value)        
        

class EmailOrPhone_field(String_field): #
    def __init__(self, *a, min_lenght=0, max_lenght=None, **k):
        self.min_lenght=min_lenght
        self.max_lenght=max_lenght
        super().__init__(*a,**k)

    def current_validation(self, value, route, main_parent):
        try:
            value=str(value)
            value=self.check_lenght(value, route)
            value.replace(' ', '')
            value=re.match(r'(.+@.+\..{1,10}$)|(\+{0,1}[0-9]{8,15}$)', value, re.I).group(0)
        except (ValueError, AttributeError, TypeError): 
            raise ValidationError(route, 'Неверный тип либо значение поля, значение поля должно быть строковой переменной, содержащей email либо номер телефона')

        return str(value)   

        
class Group_of_fields(Field):
    #Класс для полей, основа для которых словарь с элементами типа Field
  
    def __init__(self):
        super().__init__()
        self.fields=self.get_fields()

    def get_fields(self):
    #Возвращает словарь свойств объекта, у которых тип Field (поля команды)
        
        fields={attr_name:getattr(type(self), attr_name) for attr_name in dir(type(self)) if isinstance(getattr(type(self), attr_name), Field)}

        return fields
        
    def base_validation(self, data_dict, route, command_instance=None):
        if not isinstance(data_dict, dict) and self.required:
            raise ValidationError(route, 'Отсутствует обязательная группа полей')
            return None
        elif not isinstance(data_dict, dict) and not self.required:
            return self.default

        new_dict={}
    
        for key, field in self.fields.items():
            data=data_dict.get(key)
            try:
                new_dict[key]=field.validate(data, route, command_instance)
            except ValidationError as er:
                if command_instance:
                    command_instance._add_error(er.route, er.data) 
                #new_dict[key]=None 
        return new_dict                

      

class Group_list(Field):
    #Класс для полей, основа для которых список с элементами с типом Group_of_fields
    def __init__(self, group, required=True):
        self.required=required
        self.group_of_fields=group

    def base_validation(self, data_list, route, command_instance):
        if not isinstance(data_list, list) and self.required:
            raise ValidationError(route, 'Отсутствует обязательный массив(список) групп полей')
            return None
        elif not isinstance(data_list, list) and not self.required:
            return self.default
        new_list=[]
        for item in data_list:
            try:
                new_list.append(self.group_of_fields.validate(item, route, command_instance))
            except ValidationError as er:
                command_instance._add_error(er.route, er.data) 
        return new_list    
         
    def get_totals(self, data_list):
        total=0
        for item in data_list[self.get_name()]:
            total+=self.group_of_fields.get_totals(item)
        return total
        
class Product(Group_of_fields):
    name=String_field(max_lenght=255)
    paymentObject=Integer_field(allowed_values=[1,4]) #Тип продукта (1 - товар, 4 - услуга)
    paymentMethod=Integer_field(allowed_values=tuple(i for i in range(1,7)))
    quantity=Decimal_field(precision=3)
    price=Decimal_field()
    
    def get_totals(self, data_dict):
        return data_dict['price']*data_dict['quantity'].quantize(Decimal('.00'))
    
    #Метод оплаты:
    #fullPrepayment - предоплата 100% 
    #prepayment - предоплата 
    #advance - аванс 
    #fullPayment - полный расчет 
    #partialPayment - частичный расчет и кредит 
    #credit - передача в кредит 
    #creditPayment - оплата кредита    

class Payment(Group_of_fields):
    paymentType=Integer_field(allowed_values=[i for i in range(0,4)])
    summ=Decimal_field()
    
    def get_totals(self, data_dict):
        return Decimal(data_dict['summ']).quantize(Decimal('.00'))
    #Тип оплаты
    # - наличными
    # - безналичными
    # - предварительная оплата (аванс)
    # - последующая оплата (кредит)
        