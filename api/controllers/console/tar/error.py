from libs.exception import BaseHTTPException


class SceneNameDuplicateError(BaseHTTPException):
    error_code = 'scene_name_duplicate'
    description = "The scene name already exists. Please modify your scene name."
    code = 409
