from flask import Flask

from flask import render_template


from api import api

app = Flask(__name__)

app.config["SECRET_KEY"] = "CHANGE_THIS_LATER"


@app.route("/")
def home():

    return render_template(

        "index.html"

    )




app.register_blueprint(

    api,

    url_prefix="/api"

)

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )