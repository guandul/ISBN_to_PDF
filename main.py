from forms import InputBooksForm
from xml_to_data import XmlToBookData
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import os


user_xml = os.environ.get("USER_DILVE")
password = os.environ.get("PASSWORD_DILVE")

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get("DB_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# CONFIGURE TABLES


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def check_isbn(isbn):
    if len(isbn) != 13:
        return "Los ISBN tienen que ser de 13 dígitos"
    elif not isbn.isnumeric():
        return "Los ISBN tienen que ser solo números"
    elif not (isbn.startswith("978") or isbn.startswith("979")):
        return "Los ISBN tienen que empezar con 978 o 979"
    return "ok"


@app.route('/', methods=["GET", "POST"])
def home():
    return render_template("index.html")


@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(email=request.form['user']).first()
    password_input = request.form['password']
    if not user:
        error = "Usuario no es válido"
        flash(error)
        return render_template("index.html")
    else:
        if check_password_hash(user.password, password_input):
            login_user(user)
            return redirect(url_for('input_data'))
        else:
            error = "Clave incorrecta. Por favor intente de nuevo"
            flash(error)
            return render_template("index.html")


@app.route('/input_data', methods=["GET", "POST"])
@login_required
def input_data():
    form = InputBooksForm()
    if request.method == "POST":
        isbn_list = request.form["isbns"].split()

        # Check ISBN format
        for isbn in isbn_list:
            isbn = isbn.replace("-", "")
            error = check_isbn(isbn)
            if error != "ok":
                flash(error)
                return redirect("input_data")

        data = XmlToBookData(isbn_list, user_xml, password)

        data.download_covers()
        data.create_pdf()
        data.create_csv()

        error = data.error_dictionary
        flash(error)

        return redirect(url_for("success"))

    return render_template("input.html", form=form)


@app.route('/success')
@login_required
def success():
    return render_template("download.html")


@app.route('/download_pdf')
@login_required
def download_pdf():
    return send_from_directory('static', "files/recomendacion_panoplia.pdf")


@app.route('/download_csv')
@login_required
def download_csv():
    return send_from_directory('static', "files/pedido_panoplia.csv")


@app.route('/register')
def register():
    return render_template("register.html")


@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    email = request.form['user']
    if User.query.filter_by(email=email).first():
        error = "Usuario ya existe en el sistema"
        flash(error)
        return redirect(url_for("register"))

    password_encrypted = generate_password_hash(
        request.form['password'],
        method='pbkdf2:sha256',
        salt_length=8)
    user = User(
        email=email,
        password=password_encrypted
    )
    db.session.add(user)
    db.session.commit()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
