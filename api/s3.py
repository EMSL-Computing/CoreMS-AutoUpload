from minio import Minio
from api import config


def minio_init():
    minio = Minio(
        config.get("MINIO_URL", "localhost:9000")
        .replace("http://", "")
        .replace("https://", ""),
        access_key=config.get("MINIO_ROOT_USER"),
        secret_key=config.get("MINIO_ROOT_PASSWORD"),
        secure=True,
    )

    return minio


def check_create_buckets(minio, buckets_list):
    buckets = ["fticr-data", "gcms-data"]
    for bucket in buckets:
        if not minio.bucket_exists(bucket):
            minio.make_bucket(bucket)
