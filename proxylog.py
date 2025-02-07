#!/usr/bin/python3 -u

import argparse
from dotenv import load_dotenv
import os
import sys
import urllib.parse
import time
import logging

import aiohttp
import aiohttp.web
import asyncio
import json

from mysql.connector import connect, Error

target = None
target_host = None
prefix = None
max_size = None
fields = list()

connection = None
started = time.time()

log = logging.getLogger(__name__)

#log = logging.getLogger('aiohttp')
#log.setLevel(logging.DEBUG)
#log.addHandler(logging.StreamHandler(sys.stderr))

def get_args():

    load_dotenv()

    def_target = os.getenv("TARGET")
    def_prefix = os.getenv("PREFIX")
    def_fields = list(filter(None, os.getenv("FIELDS",'').split(' ')))
    def_maxsize = int(os.getenv("MAXSIZE", "50000"))


    def_dbuser = os.getenv("DBUSER")
    def_dbpass = os.getenv("DBPASS")
    def_dbname = os.getenv("DBNAME")
    def_dbhost = os.getenv("DBHOST", "localhost")


    parser = argparse.ArgumentParser(description='reverse proxy')
    parser.add_argument('-t', '--target', default=def_target,
        help=f'Target website, e.g. http://google.com  ({def_target})')
    parser.add_argument('-p', '--prefix', default=def_prefix,
        help=f'Record requests matching prefix  ({def_prefix})')
    parser.add_argument('--maxsize', default=def_maxsize,
        help=f'Do not record if payload size over maxsize ({def_maxsize})')
    parser.add_argument('-f', '--field', metavar='FIELD', nargs='+',
        default=def_fields,
        help=f'Store this field to table field f_FIELD')


    parser.add_argument('--dbuser', default=def_dbuser)
    parser.add_argument('--dbpass', default=def_dbpass)
    parser.add_argument('--dbhost', default=def_dbhost)
    parser.add_argument('--dbname', default=def_dbname)

    return parser.parse_args()

async def _info(request):
    uptime = int(time.time() - started)

    data = {
        'pid': os.getpid(),
        'remote': request.remote,
        'target': target,
        'target_host': target_host,
        'prefix': prefix,
        'uptime': uptime,
        'fields': fields
    }
    return aiohttp.web.Response(text=json.dumps(data, indent=4))

async def _sleep(request):
    start = int(time.time())

    print(f'Sleep begin pid: {os.getpid()} {id(request)}')
    await asyncio.sleep(10)
    print(f'Sleep end pid: {os.getpid()} {id(request)}')
    stop = int(time.time())

    data = {
        'start': start,
        'stop': stop
    }
    return aiohttp.web.Response(text=json.dumps(data, indent=4))


async def proxy(request):
    started = time.time()

    fnames=''
    ftpl=''

    for f in fields:
        fnames += f", f_{f}"
        ftpl += ", %s"

    insert_query = f"INSERT INTO response (method, path, code, headers, body, ms{fnames}) VALUES (%s, %s, %s, %s, %s, %s{ftpl})"

    url = urllib.parse.urljoin(target, request.path_qs)
    # print(f"proxy {request.method} {url}")
    log.debug(f"proxy {request.method} {url}")


    in_headers = dict(request.headers)
    in_headers['Host'] = target_host

    post = await request.post()

    # strip some headers
    for k in ['Content-Encoding', 'Content-Length']:
        if k in in_headers:
            del(in_headers[k])
    
    if request.method in ['GET', 'POST']:
        async with aiohttp.request(request.method, url, headers=in_headers, data=post, allow_redirects=False) as response:
            payload = await response.read()

            out_headers = dict(response.headers)
            
            for k in ['Content-Encoding', 'Content-Length', 'Transfer-Encoding']:
                if k in out_headers:
                    del(out_headers[k])

            # print(f"<{os.getpid()}> return {response.method} {response.status} u:{url}")
            if request.path.startswith(prefix) and len(payload) <= max_size:
                rfields = dict()
                try:
                    with connection.cursor() as cursor:
                        ms = int((time.time() - started)*1000)
                        values = [
                            request.method,
                            request.path_qs[:200], 
                            response.status,
                            '\n'.join([f'{k}: {v}' for k,v in response.headers.items()]),
                            payload,
                            ms]

                        for f in fields:
                            # get value
                            val = post.get(f, request.query.get(f,None))
                            values.append(val)
                            if val is not None:
                                rfields[f] = val

                        log.info(f"save {request.method} {request.path_qs} {rfields}")

                        # print("VALUES:", values)
                        cursor.execute(insert_query, values)
                        connection.commit()

                except Error as e:
                    log.error(f"MYSQL ERROR: {e}")

            return aiohttp.web.Response(body = payload,
                headers = out_headers, 
                status=response.status)
            #return response

    else:
        log.error(f"!!! ZZZZZ unsupported method {request.method}")

def makelog(name=None):
    name = name or __name__
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    log_out = logging.StreamHandler(sys.stdout)
    log_out.setLevel(logging.DEBUG)
    # h1.addFilter(lambda record: record.levelno <= logging.INFO)
    log_err = logging.StreamHandler()
    log_err.setLevel(logging.WARNING)

    formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")

    # add formatter to ch
    log_out.setFormatter(formatter)
    log_err.setFormatter(formatter)

    log.addHandler(log_out)
    log.addHandler(log_err)



def main():
    global target, target_host, prefix, fields, max_size
    global connection

    args = get_args()

    makelog()

    target = args.target
    target_host = urllib.parse.urlparse(target).netloc
    prefix = args.prefix
    fields = args.field
    max_size = args.maxsize

    app = aiohttp.web.Application()
    app.add_routes([ 
        aiohttp.web.get('/_info', _info),
        aiohttp.web.get('/_sleep', _sleep),
        aiohttp.web.get('/{tail:.*}', proxy),
        aiohttp.web.post('/{tail:.*}', proxy),
        ])



    try:
        with connect(
            host=args.dbhost,
            user=args.dbuser,
            password=args.dbpass,
            database=args.dbname,
        ) as connection:
            aiohttp.web.run_app(app)
    except Error as e:
        log.error(f"CONNECT ERR: {e}")
        log.error(f"<{os.getpid()}> Exiting...")
        sys.exit(1)


main()
