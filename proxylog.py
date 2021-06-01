#!/usr/bin/python3

import argparse
import dotenv
import os
import urllib.parse

import aiohttp
import aiohttp.web
import requests

target = None
target_host = None

def get_args():

    def_target = os.getenv('TARGET')

    parser = argparse.ArgumentParser(description='reverse proxy')
    parser.add_argument('-t', '--target', default=def_target,
        help=f'Target website, e.g. http://google.com  ({def_target})')

    return parser.parse_args()

async def handle(request):
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

            print(f"<{os.getpid()}> return {url}")

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
    global target, target_host
    args = get_args()
    target = args.target
    target_host = urllib.parse.urlparse(target).netloc

    app = aiohttp.web.Application()
    app.add_routes([ 
        aiohttp.web.get('/{tail:.*}', handle),
        aiohttp.web.post('/{tail:.*}', handle)
        ])
    aiohttp.web.run_app(app)

main()
