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
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
from dotenv import load_dotenv
from functools import wraps
from flask import session, redirect, url_for, flash


#debut app
app = Flask(__name__)

# Configuration MySQL
load_dotenv()
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)



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

    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')

    from_email = smtp_username
    subject = "Votre mot de passe temporaire pour finaliser votre inscription"
    body = f"Bonjour,\n\n" \
       f"Merci pour votre inscription en tant qu’ambassadeur 10 000 Codeurs.\n\n" \
       f"Voici votre mot de passe temporaire : {password}\n\n" \
       f"IMPORTANT :\n" \
       f"Ce mot de passe est valide pendant 5 minutes uniquement.\n" \
       f"Au-delà de ce délai, vous devrez reprendre le processus d'inscription pour recevoir un nouveau mot de passe.\n\n" \
       f"Nous vous invitons à l’utiliser immédiatement pour finaliser votre inscription.\n\n" \
       f"Bien cordialement,\n" \
       f"L’équipe 10 000 Codeurs Côte d’Ivoire"

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
                            print(f"[Cleanup] Fichier supprimé (avec timestamp) : {filepath}")
                            del last_email_sent[email]  # Optionnel
                        except Exception as e:
                            print(f"[Cleanup] Erreur suppression {filepath} : {e}")
                else:
                    # Pas de timestamp, on utilise l'heure de modification du fichier
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if now - file_mtime > timedelta(minutes=5):
                        try:
                            os.remove(filepath)
                            print(f"[Cleanup] Fichier supprimé (sans timestamp, >5min) : {filepath}")
                        except Exception as e:
                            print(f"[Cleanup] Erreur suppression {filepath} : {e}")
                    else:
                        print(f"[Cleanup] Fichier ignoré (sans timestamp, <5min) : {filepath}")
    except Exception as e:
        print(f"[Cleanup] Erreur inattendue lors du nettoyage : {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_old_files, trigger="interval", minutes=5)
scheduler.start()

# Assure-toi d'arrêter le scheduler à la fermeture propre de l'app
import atexit
atexit.register(lambda: scheduler.shutdown())

#fonction de securité accès dashboard sans être connecté
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "error")
            return redirect(url_for('connexion'))
        return f(*args, **kwargs)
    return decorated_function






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
    # Récupération des données du formulaire
    form_data = {
        'fullname': request.form['fullname'],
        'birthdate': request.form['birthdate'],
        'email': request.form['email'],
        'country': request.form['country'],
        'gender': request.form['gender'],
        'phone': request.form['phone'],
        'city': request.form['city'],
        'status': request.form['status'],
        'profile': request.form['profile'],
        'diploma': request.form['diploma'],
        'motivation': request.form['motivation'],
        'community': request.form['community']
    }

    # Fonction pour gérer les erreurs de validation
    def handle_validation_error(error_message):
        flash(error_message, "error")
        return render_template('authentification/inscription.html', 
            error_message="Le champ XYZ est invalide.",
            **form_data
        )

    # Validation formulaire
    if not form_data['fullname'] or len(form_data['fullname']) < 5 or len(form_data['fullname']) > 30:
        return handle_validation_error("Le nom complet doit contenir entre 5 et 30 caractères.")

    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\' ]+$', form_data['fullname']):
        return handle_validation_error("Le nom complet ne doit pas contenir de caractères spéciaux")

    if not form_data['birthdate']:
        return handle_validation_error("La date de naissance est requise.")

    if not re.match(r"[^@]+@[^@]+\.[^@]+", form_data['email']):
        return handle_validation_error("Veuillez entrer une adresse email valide.")
    
    # Vérifie si l'email existe déjà dans la base de données
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (form_data['email'],))
    user_exist = cursor.fetchone()
    cursor.close()

    if user_exist:
        return handle_validation_error("Cette adresse email est déjà utilisée.")

    try:
        birthdate_obj = datetime.strptime(form_data['birthdate'], '%Y-%m-%d')
        if birthdate_obj.year < 1990 or birthdate_obj.year > 2007:
            return handle_validation_error("La date de naissance doit être comprise entre 1990 et 2007.")
    except ValueError:
        return handle_validation_error("Veuillez entrer une date de naissance valide au format YYYY-MM-DD.")

    phone_normalized = form_data['phone'].replace(" ", "")
    if not re.match(r'^(\+225)?\d{10}$', phone_normalized):
        return handle_validation_error("Veuillez entrer un numéro valide (ex: +2250707070707 ou 0707070707)")

    if not form_data['city'] or len(form_data['city']) < 5 or len(form_data['city']) > 10:
        return handle_validation_error("Veuillez entrer une ville valide")

    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\' ]+$', form_data['city']):
        return handle_validation_error("Veuillez entrer une ville valide")

    # Préparation du chemin fichier Excel
    excel_dir = os.path.join(app.root_path, 'templates', 'authentification')
    excel_filename = f"data_{form_data['email']}.xlsx"
    excel_file_path = os.path.join(excel_dir, excel_filename)

    # Génération mot de passe
    password = secrets.token_urlsafe(12)

    # Création DataFrame
    data = {
        'SubmissionID': [str(uuid.uuid4())],
        'Fullname': [form_data['fullname']],
        'Birthdate': [form_data['birthdate']],
        'Email': [form_data['email']],
        'Country': [form_data['country']],
        'Gender': [form_data['gender']],
        'Phone': [form_data['phone']],
        'City': [form_data['city']],
        'Status': [form_data['status']],
        'Profile': [form_data['profile']],
        'Diploma': [form_data['diploma']],
        'Motivation': [form_data['motivation']],
        'Community': [form_data['community']],
        'Password': [password]
    }
    df = pd.DataFrame(data)
    df.to_excel(excel_file_path, index=False)
    print(f"Fichier Excel créé ou remplacé : {excel_file_path}")

    # Vérifier le délai pour envoi email
    now = datetime.now()
    if form_data['email'] in last_email_sent:
        elapsed = now - last_email_sent[form_data['email']]
        if elapsed < timedelta(minutes=5):
            flash("Un email a déjà été envoyé à cette adresse il y a moins de 5 minutes. Veuillez patienter avant de réessayer.", "warning")
            return redirect(url_for('inscription_ambassadeur'))

    # Envoi de l'email
    success = send_password_email(form_data['email'], password)
    if success:
        last_email_sent[form_data['email']] = now
        flash("Veuillez entrer le Mot de passe reçu par email", "info")
        return redirect(url_for('connexion', from_inscription='true'))
    else:
        flash("Erreur lors de l'envoi de l'email, veuillez réessayer plus tard.", "error")
        return redirect(url_for('inscription_ambassadeur'))


#connexion
@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    from_inscription = request.args.get('from_inscription') == 'true'

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Veuillez remplir tous les champs.", "error")
            return render_template('authentification/connexion.html', from_inscription=from_inscription)

        # Vérifie que le fichier Excel de cet utilisateur existe (1ère connexion)
        excel_filename = f"data_{email}.xlsx"
        excel_path = os.path.join(app.root_path, 'templates', 'authentification', excel_filename)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s", (email,))
        user = cursor.fetchone()

        if user:
            # Connexion quotidienne
            if check_password_hash(user['mdp'], password):
                session['user_id'] = user['id']
                session['email'] = user['username']
                flash("Connexion réussie !", "success")
                return redirect(url_for('index'))
            else:
                flash("Mot de passe incorrect.", "error")
                return render_template('authentification/connexion.html', from_inscription=from_inscription)
        else:
            # 1ère connexion via fichier Excel
            if not os.path.exists(excel_path):
                flash("Aucun compte associé à cet email.", "error")
                return render_template('authentification/connexion.html', from_inscription=from_inscription)

            try:
                df = pd.read_excel(excel_path)
                stored_password = df.loc[0, 'Password']
            except Exception as e:
                print(f"[Connexion] Erreur lecture fichier : {e}")
                flash("Erreur lors de la connexion. Veuillez réessayer.", "error")
                return render_template('authentification/connexion.html', from_inscription=from_inscription)

            if password == stored_password:
                hashed_password = generate_password_hash(password)
                cursor.execute("INSERT INTO users (username, mdp, role) VALUES (%s, %s, %s)",
                               (email, hashed_password, 'ambassadeur'))
                mysql.connection.commit()
                user_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO ambassadeur (
                        user_id, fullname, birthdate, email, country, gender, phone, city, statut,
                        profil, diploma, motivation, community
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    df.loc[0, 'Fullname'],
                    df.loc[0, 'Birthdate'],
                    df.loc[0, 'Email'],
                    df.loc[0, 'Country'],
                    df.loc[0, 'Gender'],
                    df.loc[0, 'Phone'],
                    df.loc[0, 'City'],
                    df.loc[0, 'Status'],
                    df.loc[0, 'Profile'],
                    df.loc[0, 'Diploma'],
                    df.loc[0, 'Motivation'],
                    df.loc[0, 'Community']
                ))
                mysql.connection.commit()

                # Connexion immédiate après inscription
                session['user_id'] = user_id
                session['email'] = email
                flash("Compte créé et connexion réussie !", "success")
                return redirect(url_for('index'))
            else:
                flash("Mot de passe incorrect.", "error")

    return render_template('authentification/connexion.html', from_inscription=from_inscription)

#deconnexion
@app.route('/deconnexion')
def deconnexion():
    session.clear()
    flash("Déconnecté avec succès.", "success")
    return redirect(url_for('connexion'))

"""
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')"""




if __name__ == '__main__':
    app.secret_key = 'admin123'
    app.run(debug=True)



