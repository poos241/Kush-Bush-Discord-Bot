from flask import Blueprint

api = Blueprint(

    "api",

    __name__

)


@api.route("/status")
def status():

    return {

        "online": True

    }