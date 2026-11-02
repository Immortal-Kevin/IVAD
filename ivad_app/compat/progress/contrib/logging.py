"""Plain log output requires no terminal progress-bar redirection."""
from contextlib import contextmanager

@contextmanager
def logging_redirect_tqdm(*args,**kwargs):
    yield
