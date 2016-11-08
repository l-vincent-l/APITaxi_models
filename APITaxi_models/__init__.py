# -*- coding: utf-8 -*-
VERSION = (0, 1, 0)
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
    import datetime
    db = SQLAlchemy(session_options={"autoflush":False})


    def validate_int(value):
        return None if value is None else int(value)

    def validate_string(value):
        assert value is None or isinstance(value, basestring)
        return value

    def validate_datetime(value):
         assert value is None or isinstance(value, datetime.datetime)
         return value

    validators = {
        db.Integer:validate_int,
        db.String:validate_string,
        db.DateTime:validate_datetime,
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
                    "Field {}: {} is not in {}".format(
                        inst.property.columns[0].name,
                        value,
                        inst.property.columns[0].type._valid_lookup.keys()
                    )
                return value
            else:
                return value
