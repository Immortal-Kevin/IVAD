"""IVAD progress-counter API for the pinned offline RF worker.

Independent IVAD implementation, NOT tqdm source or an upstream tqdm release.
GUI progress is supplied by the existing training callbacks. Terminal output
uses simple throttled log lines; notebook widgets and remote upload are absent.
"""
import sys
import threading
import time
from contextlib import contextmanager

__version__='ivad-progress-v1'

class tqdm:
    _lock=threading.RLock()
    def __init__(self,iterable=None,desc=None,total=None,initial=0,disable=False,file=None,**options):
        self.iterable=iterable
        self.total=total if total is not None else (len(iterable) if hasattr(iterable,'__len__') else None)
        self.n=initial;self.initial=initial;self.disable=disable;self.desc=desc or ''
        self.file=file or sys.stderr;self.postfix='';self.closed=False
        self.start_t=time.monotonic();self.last_print_t=self.start_t;self.last_print_n=initial
        self.unit=options.get('unit','it');self.position=options.get('position',0)
        self.pos=self.position;self.leave=options.get('leave',False)
        self.mininterval=options.get('mininterval',1.0)
        self.options=options
    def __iter__(self):
        if self.iterable is None:raise TypeError('No iterable supplied')
        try:
            for item in self.iterable:
                yield item
                self.update()
        finally:self.close()
    def __len__(self):
        if self.total is None:raise TypeError('Unknown total')
        return int(self.total)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def update(self,n=1):
        self.n+=n
        if time.monotonic()-self.last_print_t>=self.mininterval:
            self.refresh();return True
        return False
    def refresh(self,*args,**kwargs):
        if self.disable or self.closed:return
        with self.get_lock():
            print(f'[IVAD progress] {self.desc} {self.n}/{self.total if self.total is not None else "?"} {self.postfix}',file=self.file,flush=True)
        self.last_print_t=time.monotonic();self.last_print_n=self.n
    def reset(self,total=None):
        self.n=0;self.last_print_n=0;self.start_t=time.monotonic();self.closed=False
        if total is not None:self.total=total
    def close(self):self.closed=True
    def clear(self,*args,**kwargs):pass
    def unpause(self):self.last_print_t=time.monotonic()
    def set_description(self,desc=None,refresh=True):
        self.desc=desc or ''
        if refresh:self.refresh()
    set_description_str=set_description
    def set_postfix(self,ordered_dict=None,refresh=True,**kwargs):
        self.postfix=', '.join(f'{k}={v}' for k,v in dict(ordered_dict or {},**kwargs).items())
        if refresh:self.refresh()
    def set_postfix_str(self,s='',refresh=True):
        self.postfix=s
        if refresh:self.refresh()
    @property
    def format_dict(self):return dict(n=self.n,total=self.total,elapsed=time.monotonic()-self.start_t,desc=self.desc,postfix=self.postfix)
    @classmethod
    def get_lock(cls):return cls._lock
    @classmethod
    def set_lock(cls,lock):cls._lock=lock
    @staticmethod
    def write(s,file=None,end='\n',**kwargs):print(s,file=file or sys.stderr,end=end)
    @staticmethod
    def format_num(value):return str(value)
    @staticmethod
    def format_sizeof(value,suffix='',**kwargs):return f'{value}{suffix}'
    @staticmethod
    @contextmanager
    def external_write_mode(file=None,**kwargs):yield file or sys.stderr

def trange(*args,**kwargs):return tqdm(range(*args),**kwargs)
