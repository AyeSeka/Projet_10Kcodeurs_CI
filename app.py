#installation librairie
from flask import Flask,render_template,request


#debut app
app = Flask(__name__)


###############ROUTES################
#index
@app.route("/")
def index():
    return render_template("index.html")


#inscription
@app.route("/inscription_ambassadeur")
def inscription_ambassadeur():
    return render_template("authentification/inscription.html")


@app.route('/traitement_inscription_ambassadeur', methods=['POST'])
def traitement_inscription_ambassadeur():
    fullname = request.form['fullname']
    birthdate = request.form['birthdate']
    email = request.form['email']
    country = request.form['country']
    gender = request.form['gender']
    phone = request.form['phone']
    city = request.form['city']
    status = request.form['status']
    profile = request.form['profile']
    diploma = request.form['diploma']
    motivation = request.form['motivation']
    community = request.form['community']

    return render_template("authentification/confirmation.html")


if __name__ == "__main__":
    app.run(debug=True)