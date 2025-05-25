#installation librairie
from flask import Flask, request, render_template,flash,redirect, url_for
import pandas as pd
import os
import secrets
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler


#debut app
app = Flask(__name__)

############ FONCTION #############
# Dictionnaire global pour stocker la date du dernier envoi par email
last_email_sent = {}
def send_password_email(to_email, password):
    global last_email_sent
    now = datetime.now()

    # Vérifier délai 5 minutes
    if to_email in last_email_sent:
        delta = now - last_email_sent[to_email]
        if delta < timedelta(minutes=5):
            print(f"Email déjà envoyé à {to_email} il y a moins de 5 minutes. Envoi annulé.")
            return "wait"

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

        last_email_sent[to_email] = now
        return "success"

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")
        return "error"

#gestion de suppression des fichiers excel
excel_dir = os.path.join(app.root_path, 'templates', 'authentification')
def cleanup_old_files():
    try:
        if not os.path.exists(excel_dir):
            print(f"[Cleanup] Dossier non trouvé : {excel_dir}")
            return
        
        now = datetime.now()
        for filename in os.listdir(excel_dir):
            if filename.endswith('.xlsx') and filename.startswith('data_'):
                filepath = os.path.join(excel_dir, filename)
                
                # Extraire l'email depuis le nom de fichier : "data_email@example.com.xlsx"
                email = filename[len("data_"):-len(".xlsx")]
                
                # Vérifier si on a un timestamp pour cet email
                if email in last_email_sent:
                    elapsed = now - last_email_sent[email]
                    if elapsed > timedelta(minutes=5):
                        try:
                            os.remove(filepath)
                            print(f"[Cleanup] Fichier supprimé : {filepath}")
                            # Facultatif : supprimer la clé dans last_email_sent
                            del last_email_sent[email]
                        except Exception as e:
                            print(f"[Cleanup] Erreur suppression {filepath} : {e}")
                else:
                    # Pas de trace de timestamp, tu peux choisir d'ignorer ou supprimer
                    print(f"[Cleanup] Aucun timestamp pour {email}, fichier ignoré.")
    except Exception as e:
        print(f"[Cleanup] Erreur inattendue lors du nettoyage : {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_old_files, trigger="interval", minutes=2)
scheduler.start()

# Assure-toi d'arrêter le scheduler à la fermeture propre de l'app
import atexit
atexit.register(lambda: scheduler.shutdown())



############### ROUTES ################
#index
@app.route("/")
def index():
    return render_template("index.html")


#inscription
@app.route("/inscription_ambassadeur")
def inscription_ambassadeur():
    return render_template("authentification/inscription.html")


#traitement_inscription
@app.route('/traitement_inscription_ambassadeur', methods=["POST"])
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

    # Validation formulaire (inchangée)
    if not fullname or len(fullname) < 5 or len(fullname) > 30:
        flash("Le nom complet doit contenir entre 5 et 30 caractères.", "error")
        return redirect(url_for('inscription_ambassadeur'))

    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\' ]+$', fullname):
        flash("Le nom complet ne doit pas contenir de caractères spéciaux", "error")
        return redirect(url_for('inscription_ambassadeur'))

    if not birthdate:
        flash("La date de naissance est requise.", "error")
        return redirect(url_for('inscription_ambassadeur'))

    try:
        birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d')
        if birthdate_obj.year < 2007:
            flash("La date de naissance ne doit pas être antérieure à l'année 2007.", "error")
            return redirect(url_for('inscription_ambassadeur'))
    except ValueError:
        flash("Veuillez entrer une date de naissance valide au format YYYY-MM-DD.", "error")
        return redirect(url_for('inscription_ambassadeur'))

    phone_normalized = phone.replace(" ", "")
    if not re.match(r'^(\+225)?\d{10}$', phone_normalized):
        flash("Veuillez entrer un numéro valide (ex: +2250707070707 ou 0707070707)", "error")
        return redirect(url_for('inscription_ambassadeur'))

    if not city or len(city) < 5 or len(city) > 10:
        flash("Veuillez entrer une ville valide", "error")
        return redirect(url_for('inscription_ambassadeur'))

    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\' ]+$', city):
        flash("Veuillez entrer une ville valide", "error")
        return redirect(url_for('inscription_ambassadeur'))

    # Préparation du chemin fichier Excel
    excel_dir = os.path.join(app.root_path, 'templates', 'authentification')
    excel_filename = f"data_{email}.xlsx"
    excel_file_path = os.path.join(excel_dir, excel_filename)

    # Génération mot de passe
    password = secrets.token_urlsafe(12)

    # Création DataFrame
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
    df.to_excel(excel_file_path, index=False)
    print(f"Fichier Excel créé ou remplacé : {excel_file_path}")

    # Vérifier le délai pour envoi email
    now = datetime.now()
    if email in last_email_sent:
        elapsed = now - last_email_sent[email]
        if elapsed < timedelta(minutes=5):
            flash("Un email a déjà été envoyé à cette adresse il y a moins de 5 minutes. Veuillez patienter avant de réessayer.", "warning")
            return redirect(url_for('inscription_ambassadeur'))

    # Envoi de l'email
    success = send_password_email(email, password)
    if success:
        last_email_sent[email] = now
        flash("Veuillez entrer le Mot de passe reçu par email", "info")
        return render_template("authentification/connexion.html")
    else:
        flash("Erreur lors de l'envoi de l'email, veuillez réessayer plus tard.", "error")
        return redirect(url_for('inscription_ambassadeur'))

if __name__ == '__main__':
    app.secret_key = 'admin123'
    app.run(debug=True)



