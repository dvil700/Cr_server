from datetime import timedelta
from wtforms.ext.csrf.session import SessionSecureForm


class CsrfForm(SessionSecureForm):
    SECRET_KEY = b'EPj00jpfj8Gx1SjnyLxwBBSQfnQ9DJYe0Ym'
    TIME_LIMIT = timedelta(minutes=20)