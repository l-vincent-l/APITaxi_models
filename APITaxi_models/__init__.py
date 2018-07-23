# -*- coding: utf-8 -*-
VERSION = (0, 1, 1)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))
__doc__ = "Models used by APITaxi"
try:
    from flask_sqlalchemy import SQLAlchemy
except ImportError:
    db = None
else:
    from sqlalchemy import event
    import datetime, aniso8601, functools
    db = SQLAlchemy(session_options={"autoflush":False})


    def validate_int(value):
        return None if value is None else int(value)

    def validate_string(value):
        assert value is None or isinstance(value, basestring)
        return value

    def validate_datetime(value):
        if value is None:
            return value
        elif isinstance(value, datetime.datetime):
            return value
        else:
            try:
                aniso8601.parse_datetime(value, delimiter='T')
            except ValueError:
                raise AssertionError("{} is not a Datetime".format(value))
            return value

    def validate_date(value):
        if value is None:
            return value
        elif isinstance(value, datetime.date):
            return value
        else:
            func = validate_datetime if "T" in value else aniso8601.parse_date
            try:
                func(value)
            except ValueError:
                raise AssertionError("{} is not a Date".format(value))
            return value


    validators = {
        db.Integer:validate_int,
        db.String:validate_string,
        db.DateTime:validate_datetime,
        db.Date: validate_date,
    }

    @event.listens_for(db.Model, 'attribute_instrument')
    def configure_listener(class_, key, inst):
        if not hasattr(inst.property, 'columns'):
            return
        @event.listens_for(inst, "set", retval=True)
        def set_(instance, value, oldvalue, initiator):
            _class = inst.property.columns[0].type.__class__
            validator = validators.get(_class)
            if validator:
                return validator(value)
            elif _class is db.Enum:
                assert value in inst.property.columns[0].type._valid_lookup,\
                    "Error with field {}: {} is not in {}".format(
                        inst.property.columns[0].name,
                        value,
                        inst.property.columns[0].type._valid_lookup.keys()
                    )
                return value
            else:
                return value

    from .departement import Departement
    from .zupc import ZUPC
    from .driver import Driver
    from .customer import Customer
    from .constructor import Constructor
    from .model import Model
    from .vehicle_description import VehicleDescription
    from .vehicle import Vehicle
    from .ads import ADS
    from .taxis import Taxi, RawTaxi, TaxiRedis
    from .hail import Hail, HailLog
