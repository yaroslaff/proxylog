#!/usr/bin/python3

import argparse
from dotenv import load_dotenv
import os
import sys
import urllib.parse

import aiohttp
import aiohttp.web
import time
import json

from mysql.connector import connect, Error

target = None
target_host = None
prefix = None

connection = None


def get_args():

    load_dotenv()

    def_target = os.getenv("TARGET")
    def_prefix = os.getenv("PREFIX")

    def_dbuser = os.getenv("DBUSER")
    def_dbpass = os.getenv("DBPASS")
    def_dbname = os.getenv("DBNAME")
    def_dbhost = os.getenv("DBHOST", "localhost")

    parser = argparse.ArgumentParser(description='reverse proxy')
    parser.add_argument('-t', '--target', default=def_target,
        help=f'Target website, e.g. http://google.com  ({def_target})')
    parser.add_argument('-p', '--prefix', default=def_prefix,
        help=f'Record requests matching prefix  ({def_prefix})')

    parser.add_argument('--dbuser', default=def_dbuser)
    parser.add_argument('--dbpass', default=def_dbpass)
    parser.add_argument('--dbhost', default=def_dbhost)
    parser.add_argument('--dbname', default=def_dbname)

    return parser.parse_args()

async def _info(request):
    data = {
        'target': target,
        'target_host': target_host,
        'prefix': prefix
    }
    return aiohttp.web.Response(text=json.dumps(data, indent=4))

async def proxy(request):
    started = time.time()

    insert_query = "INSERT INTO response (path, code, headers, body, ms) VALUES (%s, %s, %s, %s, %s)"

    url = target + request.path_qs
    print(f"<{os.getpid()}> forward to {request.method} {url}")

    in_headers = dict(request.headers)
    in_headers['Host'] = target_host

    post = await request.post()

    if request.method in ['GET', 'POST']:
        async with aiohttp.request(request.method, url, data=post, allow_redirects=False) as response:
            payload = await response.read()

            out_headers = dict(response.headers)
            
            for k in ['Content-Encoding', 'Content-Length']:
                if k in out_headers:
                    del(out_headers[k])

            print(f"<{os.getpid()}> return s:{response.status} u:{url}")

            if request.path.startswith(prefix):
                print("SAVE TO DB")
                with connection.cursor() as cursor:
                    ms = int((time.time() - started)*1000)
                    values = (
                        request.path_qs, 
                        response.status,
                        '\n'.join([f'{k}: {v}' for k,v in response.headers.items()]),
                        payload,
                        ms)
                    print(values)
                    cursor.execute(insert_query, values)
                    connection.commit()

            return aiohttp.web.Response(body = payload,
                headers = out_headers, 
                status=response.status)
            #return response

    else:
        print(f"!!! ZZZZZ unsupported method {request.method}")


    payload = ('x'*50 + '\n')*10
    print("QQQQQQQQQQQQQQQQQQq")
    return aiohttp.web.Response(body = payload, 
        status=r.status_code, 
        headers=r.headers)

def main():
    global target, target_host, prefix
    global connection

    args = get_args()
    target = args.target
    target_host = urllib.parse.urlparse(target).netloc
    prefix = args.prefix

    app = aiohttp.web.Application()
    app.add_routes([ 
        aiohttp.web.get('/_info', _info),
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
        print(e)
        sys.exit(1)


main()
