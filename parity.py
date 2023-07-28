#!/usr/bin/python3

import argparse
import os
import subprocess
from datetime import datetime, timezone, timedelta

def _par2create(filename):
  return ['par2create', '-r5', '-n1', '-m3000', '-q', filename]

def _par2verify(filename):
  return ['par2verify', filename]

def _list_files(prefix):
  return [f for f in os.listdir('.') if os.path.isfile(f) and f.startswith(prefix)]

def parity_create(prefix):
  files = _list_files(prefix)
  for f in files:
    if f + '.par2' in files or f.endswith('.par2'):
      continue
    r = subprocess.run(_par2create(f))
    if r.returncode != 0:
      print('Something went wrong generating a parity file!')
      exit(r.returncode)

def parity_verify(prefix):
  files = _list_files(prefix)
  for f in files:
    if f.endswith('.par2'):
      r = subprocess.run(_par2verify(f))
      if r.returncode != 0:
        print('Something went wrong verifying a file!')
        exit(r.returncode)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Automatically run par2 on a given filename prefix.')
  parser.add_argument('--prefix', type=str, help='Prefix of the filenames.')
  parser.add_argument('--create', action='store_true', help='Create the parity files.')
  parser.add_argument('--verify', action='store_true', help='Verify existing parity files.')

  args = parser.parse_args()

  if args.create and args.verify:
    print('Cannot pass in both --create and --verify!')
    exit(1)
  elif not args.verify:
    args.create = True

  if args.create:
    parity_create(args.prefix)
  elif args.verify:
    parity_verify(args.prefix)