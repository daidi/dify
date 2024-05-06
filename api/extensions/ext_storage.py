from collections.abc import Generator
from typing import Union

from flask import Flask

from extensions.storage.aliyun_storage import AliyunStorage
from extensions.storage.azure_storage import AzureStorage
from extensions.storage.google_storage import GoogleStorage
from extensions.storage.local_storage import LocalStorage
from extensions.storage.s3_storage import S3Storage


class Storage:
    def __init__(self):
        self.storage_runner = None

    def init_app(self, app: Flask):
        storage_type = app.config.get('STORAGE_TYPE')
        if storage_type == 's3':
            self.storage_runner = S3Storage(
                app=app
            )
        elif storage_type == 'azure-blob':
            self.storage_runner = AzureStorage(
                app=app
            )
        elif storage_type == 'aliyun-oss':
            self.storage_runner = AliyunStorage(
                app=app
            )
        elif storage_type == 'google-storage':
            self.storage_runner = GoogleStorage(
                app=app
            )
        else:
            self.storage_runner = LocalStorage(app=app)

    def save(self, filename, data):
        self.storage_runner.save(filename, data)

    def load(self, filename: str, stream: bool = False) -> Union[bytes, Generator]:
        if stream:
            return self.load_stream(filename)
        else:
            return self.load_once(filename)

    def load_once(self, filename: str) -> bytes:
        return self.storage_runner.load_once(filename)

    def ensure(self, filename: str) -> bool:
        if not self.folder or self.folder.endswith('/'):
            filename = self.folder + filename
        else:
            filename = self.folder + '/' + filename

        if os.path.exists(filename):
            return True
        folder = os.path.dirname(filename)
        os.makedirs(folder, exist_ok=True)

        if self.storage_type == 's3':
            try:
                with closing(self.client) as client:
                    data = client.get_object(Bucket=self.bucket_name, Key=filename)['Body'].read()
                    if not self.folder or self.folder.endswith('/'):
                        filename = self.folder + filename
                    else:
                        filename = self.folder + '/' + filename
            except ClientError as ex:
                if ex.response['Error']['Code'] == 'NoSuchKey':
                    raise FileNotFoundError("File not found")
                else:
                    raise

            with open(os.path.join(os.getcwd(), filename), "wb") as f:
                f.write(data)
            return True
        elif self.storage_type == 'azure-blob':
            blob = self.client.get_container_client(container=self.bucket_name)
            blob = blob.get_blob_client(blob=filename)
            data = blob.download_blob().readall()

            with open(os.path.join(os.getcwd(), filename), "wb") as f:
                f.write(data)
            return True

        return False

    def load_stream(self, filename: str) -> Generator:
        return self.storage_runner.load_stream(filename)

    def download(self, filename, target_filepath):
        self.storage_runner.download(filename, target_filepath)

    def exists(self, filename):
        return self.storage_runner.exists(filename)

    def delete(self, filename):
        return self.storage_runner.delete(filename)


storage = Storage()


def init_app(app: Flask):
    storage.init_app(app)
