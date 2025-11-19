from flask_smorest import Api

def init_api(app, version):
    from .v1 import annotation, annotation_class, project, image, notification, setting, tile, misc, ray
    app.config[f"{version.upper()}_API_TITLE"] = "QuickAnnotator_API"
    app.config[f"{version.upper()}_API_VERSION"] = version
    app.config[f"{version.upper()}_OPENAPI_VERSION"] = "3.0.2"
    app.config[f"{version.upper()}_OPENAPI_URL_PREFIX"] = f"/api/{version}"
    app.config[f"{version.upper()}_OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config[f"{version.upper()}_OPENAPI_SWAGGER_UI_URL"] = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/"
    api = Api(app, config_prefix=f"{version.upper()}_", )
    blueprints = [
        (annotation.bp, "/annotation"),
        (annotation_class.bp, "/class"),
        (project.bp, "/project"),
        (image.bp, "/image"),
        (notification.bp, "/notification"),
        (setting.bp, "/setting"),
        (tile.bp, "/tile"),
        (misc.bp, "/misc"),
        (ray.bp, "/ray"),
    ]

    prefix = app.config[f"{version.upper()}_OPENAPI_URL_PREFIX"]
    for bp, url in blueprints:
        api.register_blueprint(bp, url_prefix=prefix + url)
    return api