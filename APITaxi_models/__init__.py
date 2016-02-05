# -*- coding: utf-8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))
__doc__ = "Models used by APITaxi"
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(session_options={"autoflush":False})
