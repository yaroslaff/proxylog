import argparse
import dotenv
import os

def get_args():

    def_target = os.getenv('TARGET')

    parser = argparse.ArgumentParser(description='reverse proxy')
    parser.add_argument('-t', '--target', default=def_target,
        help=f'Target website, e.g. http://google.com/  ({def_target})')

def main():
    args = get_args()
    print(args)

main()