# Incremental Backup from ZFS to AWS

Incremental backup script for exporting ZFS snapshots to AWS.

This is a script I use to automatically generate incremental backups of my data and upload them to my AWS S3 bucket.

Maybe it'll be useful for others too.

It requires that you use ZFS on a *nix system and have the AWS S3 client available.

How to run:

```$ backup.py --pool your_zfs_filesystem --dataset your_zfs_dataset --aws_bucket your_aws_bucket --aws_cli path/to/aws/cli --config "config.json"```

Note the `--config` flag is for pointing to a JSON file that stores your encryption passwords, which follows this format:
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

Also note the `--aws_cmd` is expecting an executable path to which you can append an `s3` command.

I use the Docker [aws-cli](https://hub.docker.com/r/amazon/aws-cli) container with a `aws.sh` script:
```sh
#!/bin/bash
docker run --rm -t $(tty &>/dev/null && echo "-i") -e "AWS_ACCESS_KEY_ID=your_key" -e "AWS_SECRET_ACCESS_KEY=your_secret_key" -e "AWS_DEFAULT_REGION=your_region" -v "$(pwd):/aws" amazon/aws-cli "$@"
```

So my command would have `--aws_cli /path/to/aws.sh`.