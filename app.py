#installation librairie
from flask import Flask, request, render_template
import pandas as pd
import os
import secrets
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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


# Fonction pour envoyer un email avec le mot de passe généré
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_email(to_email, password):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_username = 'seka.aye@uvci.edu.ci'
    smtp_password = 'xhzc fvwf kmjq ktib'
    
    from_email = smtp_username
    subject = 'Votre mot de passe généré'
    body = f"Bonjour,\n\nVoici votre mot de passe généré : {password}\n\nMerci."

    message = MIMEMultipart()
    message['From'] = from_email
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        print("Connexion au serveur SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        print("Connexion réussie. Authentification...")
        server.login(smtp_username, smtp_password)
        print("Authentification réussie. Envoi de l'email...")
        server.sendmail(from_email, to_email, message.as_string())
        print(f"Email envoyé à {to_email} avec le mot de passe.")
        server.quit()
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")






@app.route('/traitement_inscription_ambassadeur', methods=["POST"])
def traitement_inscription_ambassadeur():
    # Récupération des données du formulaire
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

    # Génération d'un mot de passe aléatoire sécurisé
    password = secrets.token_urlsafe(12)

    # Création du DataFrame avec les données du formulaire et un identifiant unique
    data = {
        'SubmissionID': [str(uuid.uuid4())],
        'Fullname': [fullname],
        'Birthdate': [birthdate],
        'Email': [email],
        'Country': [country],
        'Gender': [gender],
        'Phone': [phone],
        'City': [city],
        'Status': [status],
        'Profile': [profile],
        'Diploma': [diploma],
        'Motivation': [motivation],
        'Community': [community],
        'Password': [password]
    }
    df = pd.DataFrame(data)

    # Définir le chemin pour sauvegarder le fichier Excel
    excel_dir = os.path.join(app.root_path, 'templates', 'authentification')
    excel_filename = f"data_{email}.xlsx"
    excel_file_path = os.path.join(excel_dir, excel_filename)

    # Écraser le fichier s'il existe ou créer un nouveau
    df.to_excel(excel_file_path, index=False)
    print(f"Fichier Excel créé ou remplacé : {excel_file_path}")

    # Envoyer un email avec le mot de passe généré
    send_password_email(email, password)

    # Renvoyer la page de confirmation
    return render_template("authentification/confirmation.html")

if __name__ == '__main__':
    app.run(debug=True)



