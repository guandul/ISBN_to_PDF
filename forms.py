from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.widgets import TextArea

# WTForm


class InputBooksForm(FlaskForm):
    isbns = StringField("Lista de ISBNs", widget=TextArea())


# class UserForm(FlaskForm):
#     email = StringField("Email", validators=[DataRequired(), Email()])
#     password = PasswordField("Password", validators=[DataRequired()])
#     submit = SubmitField("Register")


