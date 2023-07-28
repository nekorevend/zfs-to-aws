#!/usr/bin/python3

import argparse
import os
import re
import subprocess
import json
from datetime import datetime, timezone, timedelta, date
from parity import parity_create

def to_iso8601(dt):
  return dt.strftime('%Y%m%d')

def from_iso8601(ts):
  return datetime.strptime(ts, '%Y%m%d')

def today_iso8601():
  return date.today().strftime('%Y%m%d')

def get_filename_prefix(dataset, from_date, to_date):
  return '{}-F{}-T{}-part-'.format(
                                    dataset,
                                    to_iso8601(from_date),
                                    to_iso8601(to_date)
                                  )

def _aws_ls(dataset, aws_bucket, aws_cli):
  return [
          aws_cli,
          's3',
          'ls',
          '{}/{}/incrementals/'.format(aws_bucket, dataset)
         ]

def _zfs_list_snapshot(pool, dataset):
  return ['zfs', 'list', '{}/{}'.format(pool, dataset), '-t', 'snapshot']

def _zfs_snapshot(pool, dataset, tag, date):
  return ['zfs', 'snapshot', '{}/{}@{}-{}'.format(pool, dataset, tag, to_iso8601(date))]

def _zfs_send_i(pool, dataset, tag, from_date, to_date):
  return ['zfs', 'send', '-I', '{}/{}@{}-{}'.format(
      pool,
      dataset,
      tag,
      to_iso8601(from_date),
    ), '{}/{}@{}-{}'.format(
      pool,
      dataset, 
      tag,
      to_iso8601(to_date)
    )
    ]

def _zfs_encrypt_parts(pool, dataset, tag, from_date, to_date, data):
  zfs_send = _zfs_send_i(pool, dataset, tag, from_date, to_date)
  openssl = ['openssl', 'enc', '-aes-256-cbc', '-md', 'sha512', '-pbkdf2', '-iter', '250000', '-pass', 'pass:{}'.format(data[dataset]['pass'])]
  split = ['split', '-b', '4G', '--suffix-length=6', '-', get_filename_prefix(dataset, from_date, to_date)
    ]
  return [zfs_send, openssl, split]

def local_find_latest_snapshot(pool, dataset, tag):
  process = subprocess.run(_zfs_list_snapshot(pool, dataset), stdout=subprocess.PIPE, universal_newlines=True)
  snapshots = []
  for line in process.stdout.split('\n'):
    m = re.search('{}\/{}@{}-(\d+)'.format(pool, dataset, tag), line)
    if m:
      snapshots.append(m.group(1))
  snapshots.sort()
  return snapshots[-1]

def aws_find_latest(aws_bucket, dataset, tag, aws_cli):
  process = subprocess.run(_aws_ls(dataset, aws_bucket, aws_cli), stdout=subprocess.PIPE, universal_newlines=True)
  dates = []
  for line in process.stdout.split('\n'):
    m = re.search('PRE\sF(\d+)-T(\d+)\/', line)
    if m:
      dates.append(m.group(2))
  dates.sort()
  return dates[-1]

def _aws_upload(dataset, aws_cli, aws_bucket, from_date, to_date):
  from_date_str = to_iso8601(from_date)
  to_date_str = to_iso8601(to_date)
  return [aws_cli,
          's3',
          'sync',
          '--exclude',
          '*',
          '--include',
          '{}*'.format(get_filename_prefix(dataset, from_date, to_date)),
          '.',
          's3://{}/{}/incrementals/F{}-T{}'.format(aws_bucket, dataset, from_date_str, to_date_str),
          '--storage-class',
          'DEEP_ARCHIVE'
         ]

def upload_to_aws(dataset, aws_cli, aws_bucket, from_date, to_date):
  subprocess.run(_aws_upload(dataset, aws_cli, aws_bucket, from_date, to_date))

def export_and_encrypt(pool, dataset, tag, from_date, to_date, data):
  cmds = _zfs_encrypt_parts(pool, dataset, tag, from_date, to_date, data)
  with subprocess.Popen(cmds[0], stdout=subprocess.PIPE) as c1:
    with subprocess.Popen(cmds[1], stdout=subprocess.PIPE, stdin=c1.stdout) as c2:
      subprocess.run(cmds[2], stdin=c2.stdout)

def create_snapshot_if_needed(pool, dataset, tag, date):
  # Only create if the desired date is today.
  date_str = to_iso8601(date)
  if today_iso8601() == date_str and date_str != local_find_latest_snapshot(pool, dataset, tag):
    subprocess.run(_zfs_snapshot(pool, dataset, tag, date))

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Backup a dataset to AWS.')
  parser.add_argument('--pool', required=True, type=str, help='Name of zfs pool. e.g. tank1')
  parser.add_argument('--dataset', required=True, type=str, help='Name of zfs dataset. e.g. documents')
  parser.add_argument('--aws_bucket', required=True, type=str, help='Name of the AWS S3 storage bucket.')
  parser.add_argument('--aws_cli', required=True, type=str, help='Path to the AWS CLI executable.')
  parser.add_argument('--config', required=True, help='Path to config file.')
  parser.add_argument('--from_date', type=str, help='End date in "YYYYMMDD". e.g. 20220610')
  parser.add_argument('--to_date', default=today_iso8601(), help='End date in "YYYYMMDD". e.g. 20220610')
  parser.add_argument('--tag', default='offsite', help='Prefix of the snapshot name.')

  args = parser.parse_args()

  if not args.from_date:
    args.from_date = aws_find_latest(args.aws_bucket, args.dataset, args.tag, args.aws_cli)

  data = {}
  with open(args.config) as config:
    data = json.load(config)

  if args.dataset not in data.keys():
    print('dataset "{}" does not exist in the config file.'.format(args.dataset))
    exit(1)

  if args.from_date == args.to_date:
    print('From and To are the same date. Skipping.')
    exit(0)

  create_snapshot_if_needed(args.pool, args.dataset, args.tag, from_iso8601(args.to_date))
  export_and_encrypt(args.pool, args.dataset, args.tag, from_iso8601(args.from_date), from_iso8601(args.to_date), data)
  parity_create(get_filename_prefix(args.dataset, from_iso8601(args.from_date), from_iso8601(args.to_date)))
  upload_to_aws(args.dataset, args.aws_cli, args.aws_bucket, from_iso8601(args.from_date), from_iso8601(args.to_date))