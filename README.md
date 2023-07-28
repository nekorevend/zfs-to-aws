# Incremental Backup from ZFS to AWS

Incremental backup script for exporting ZFS snapshots to AWS.

This is a tool I use to automatically generate incremental backups of my data and upload them to my AWS S3 bucket. This tool exists to implement two features I wanted:
1. Self-encryption of my data.
1. Inclusion of parity data in case the backup experiences bit-rot.

I wrote about the reasoning and design of this tool in detail [here](https://victorchang.codes/automating-incremental-backups-to-aws).

Maybe it'll be useful for others too, but note that my initial baseline backup was hand-made and this script currently only works toward generating the incremental backups. **You must first handle creating the baseline backup that the incremental backups build on.**

The tool requires that you use ZFS on a *nix system and have the AWS S3 client available.

Specifically, you need `aws`, `openssl`, `par2create`, `split`, and `zfs` available in your terminal.

## How to run

```$ ./backup.py --pool your_zfs_filesystem --dataset your_zfs_dataset --aws_bucket your_aws_bucket --aws_cli path/to/aws/cli --config /path/to/config.json```

### Special notes for some flags

#### --config

The `--config` flag is for pointing to a JSON file that stores your encryption passwords, which follows this format:
```json
{
    "my_dataset_A": {
        "pass": "my_password"
    },
    "my_dataset_B": {
        "pass": "my_password2"
    },
}
```

**Put special care into escaping the special characters in your password!**

#### --aws_cli

The `--aws_cli` is expecting an executable path to which you can append an `s3` command.

I use the Docker [aws-cli](https://hub.docker.com/r/amazon/aws-cli) container with an `aws.sh` script:
```sh
#!/bin/bash
docker run --rm -t $(tty &>/dev/null && echo "-i") -e "AWS_ACCESS_KEY_ID=your_key" -e "AWS_SECRET_ACCESS_KEY=your_secret_key" -e "AWS_DEFAULT_REGION=your_region" -v "$(pwd):/aws" amazon/aws-cli "$@"
```

So my command would have `--aws_cli /path/to/aws.sh`.

## Future Work
- Enable the script to create the baseline backup files.
- Automate downloading and restoring from backup.