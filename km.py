from datetime import datetime
import os
import socket
import sys
import time
import urllib
import urllib2
import urlparse

class KM(object):
    _id = None
    host = 'trk.kissmetrics.com:80'
    log_dir = '/tmp'
    _key = None
    _logs = {}
    _to_stderr = True
    _use_cron = None

    @classmethod
    def init(cls, key, host=None, log_dir=None, use_cron=None, to_stderr=None):
        cls._key = key
        if host is not None:
            cls.host = host
        if log_dir is not None:
            cls.log_dir = log_dir
        if use_cron is not None:
            cls._use_cron = use_cron
        if to_stderr is not None:
            cls._to_stderr = to_stderr
        try:
            cls.log_dir_writable()
        except Exception, e:
            cls.log_error(e)

    @classmethod
    def identify(cls, id):
        cls._id = id

    @classmethod
    def record(cls, action, props={}):
        try:
            if not cls.is_initialized_and_identified():
                return
            if isinstance(action, dict):
                return cls.set(action)

            props.update({'_n': action})
            cls.generate_query('e', props)
        except Exception, e:
            cls.log_error(e)

    @classmethod
    def alias(cls, name, alias_to):
        try:
            if not cls.is_initialized_and_identified():
                return
            cls.generate_query('a', {'_n': alias_to, '_p': name}, update=False)
        except Exception, e:
            cls.log_error(e)

    @classmethod
    def set(cls, data):
        try:
            if not cls.is_initialized_and_identified():
                return
            cls.generate_query('s', data)
        except Exception, e:
            cls.log_error(e)

    @classmethod
    def log_file(cls):
        return '/tmp/kissmetrics_error.log'

    @classmethod
    def reset(cls):
        cls._id = None
        cls._key = None
        cls._logs = {}

    @classmethod
    def check_identify(cls):
        if cls._id == None:
            raise Exception("Need to identify first (KM.identify <user>)")

    @classmethod
    def check_init(cls):
        if cls._key == None:
            raise Exception("Need to initialize first (KM.init <your_key>)")

    @classmethod
    def now(cls):
        return datetime.now()

    @classmethod
    def check_id_key(cls):
        cls.check_init()
        cls.check_identify()

    @classmethod
    def logm(cls, msg):
        msg = cls.now().strftime('<%c> ') + msg
        try:
            fh = open(cls.log_file(), 'a')
            fh.write(msg)
            fh.close()
        except IOError:
            pass #just discard at this point

    @classmethod
    def request(cls, type, data, update=True):
        query = []
        data.update({'_k': cls._key, '_t': cls.now().strftime('%s')})
        if update:
            data.update({'_p': cls._id})

        for key, val in data.items():
            query.append(urllib.quote(str(key)) + '=' + urllib.quote(str(val)))

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host, port = cls.host.split(':')
            sock.connect((host, int(port)))
            sock.setblocking(0) # 0 is non-blocking

            get = 'GET /' + type + '?' + '&'.join(query) + " HTTP/1.1\r\n"
            out = get
            out += "Host: " + socket.gethostname() + "\r\n"
            out += "Connection: Close\r\n\r\n"
            sock.send(out)
            sock.close()
        except:
            cls.logm("Could not transmit to " + cls.host)

    @classmethod
    def log_name(cls, type):
        if type in cls._logs:
            return cls._logs[type]
        fname = ''
        if type == 'error':
            fname = 'kissmetrics_error.log'
        elif type == 'query':
            fname = 'kissmetrics_query.log'
        elif type == 'send':
            fname = '%dkissmetrics_sending.log' % time.time()
        cls._logs[type] = os.path.join(cls.log_dir, fname)
        return cls._logs[type]

    @classmethod
    def log_query(cls, msg):
        return cls.log('query', msg)

    @classmethod
    def log_error(cls, msg):
        msg = datetime.now().strftime("<%c> ") + str(msg)
        if cls._to_stderr:
            print >>sys.stderr, msg
        return cls.log('error', msg)

    @classmethod
    def log(cls, type, msg):
        try:
            fh = open(cls.log_name(type), 'a')
            print >>fh, msg
            fh.close()
        except:
            pass                        # just discard at this point

    @classmethod
    def generate_query(cls, type, data, update=True):
        if update:
            data.update({'_p': cls._id})
        data.update({'_k': cls._key, '_t': int(time.time())})
        query = '/%s?%s' % (urllib.quote(type), urllib.urlencode(data))
        if cls._use_cron:
            cls.log_query(query)
        else:
            try:
                cls.send_query(query)
            except Exception, e:
                cls.log_query(query)
                cls.log_error(e)

    @classmethod
    def send_query(cls, line):
        url = urlparse.urlunsplit(('http', cls.host, line, '', ''))
        urllib2.urlopen(url)

    @classmethod
    def log_dir_writable(cls):
        if not os.access(cls.log_dir, os.W_OK) and cls._to_stderr:
            print >>sys.stderr, (
                "Couldn't open %s for writing. Does %s exist? Permissions?" %
                (cls.log_name('query'), cls.log_dir)
            )

    @classmethod
    def is_identified(cls):
        if cls._id is None:
            cls.log_error("Need to identify first: KM.identify(<user>)")
            return False
        return True

    @classmethod
    def is_initialized_and_identified(cls):
        if not cls.is_initialized():
            return False
        return cls.is_identified()

    @classmethod
    def is_initialized(cls):
        if cls._key is None:
            cls.log_error("Need to initialize first: KM.init(<your_key>)")
            return False
        return True
