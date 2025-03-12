#first we import flask
from re import template
from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
#from data import Articles
import os
os.environ['DYLD_LIBRARY_PATH'] = '/usr/local/mysql-8.0.28-macos11-x86_64/lib'  # or the path to your MySQL client library
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, BooleanField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '/path/to/the/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

#create an instance of the flask class
#its a place holder for the current module(app.y)
app = Flask(__name__)

#config Mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Tronstar123'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#initMysql
#db = app.mysql.connect()
#cursor= db.cursor()
mysql = MySQL(app)

#Articles = Articles()

#Index
@app.route('/')
def index():
    return render_template('home.html')

#About
@app.route('/about')
def about():
    return render_template('about.html')

#Articles
@app.route('/articles')
def articles():
    #Create cursor
    cur = mysql.connection.cursor()
    
    #Get articles
    result = cur.execute("SELECT * FROM articles")
    
    articles = cur.fetchall()
    
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'NO ARTICLES FOUND'
        return render_template('articles.html', msg=msg)
    #Close connection
    cur.close()

#Single article
@app.route('/article/<string:id>/')
def article(id):
    #Create cursor
    cur = mysql.connection.cursor()
    
    #Get article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    
    article = cur.fetchone()
    return render_template('article.html', article=article)

#Register Form Class
class RegistrationForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password')

#User Register    
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():  
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        
        #Create cursor
        cur = mysql.connection.cursor()
        
        #Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
        
        #Commit to DB
        mysql.connection.commit()
        
        #Close connection
        cur.close()
        
        #Flash messages
        flash("You are now registered and can log in", "success")
        
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

#User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #Get form fields
        username = request.form['username']
        password_candidate = request.form['password']
        
        #Create cursor
        cur = mysql.connection.cursor()
        
        #Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
        
        if result > 0:
            #Get stored hash
            data = cur.fetchone()
            password = data['password']
            
            #Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                #app.logger.info('PASSWORD MATCHED')
                #PASSED
                session['logged_in'] = True
                session['username'] = username
                
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            #CLOSE CONNECTION
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
        
    return render_template('login.html')

#Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in'in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized access, Please Login","danger")
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
@is_logged_in
def logout():
    # clear the session
    session.clear()     
    flash("You have been logged out","success")
    # send them back to home page
    return redirect(url_for('login'))   

#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    #Create cursor
    cur = mysql.connection.cursor()
    
    #Get articles
    result = cur.execute("SELECT * FROM articles")
    
    articles = cur.fetchall()
    
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'NO ARTICLES FOUND'
        return render_template('dashboard.html', msg=msg)
    #Close connection
    cur.close()

#Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])
    
#Add Article
@app.route('/add_article', methods = ['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        
        #Create Cursor
        cur = mysql.connection.cursor()
        
        #Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))
        
        #Commit to DB
        mysql.connection.commit()
        
        #Close connection
        cur.close()
        
        flash("Article Created", "danger")
        
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)
    
#Edit Article
@app.route('/edit_article/<string:id>', methods = ['GET', 'POST'])
@is_logged_in
def edit_article(id):
    
    #Create cursor
    cur = mysql.connection.cursor()
    
    #Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    
    article = cur.fetchone()
    cur.close()
    
    #Get form/ article from owner
    form = ArticleForm(request.form)
    
    #Populate article fields with data from db
    form.title.data = article['title']
    form.body.data = article['body']
    
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        
        #Create Cursor
        cur = mysql.connection.cursor()
        
        #Execute
        cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s",(title, body, id))
        
        #Commit to DB
        mysql.connection.commit()
        
        #Close connection
        cur.close()
        
        flash('Article Updated', 'success')
        
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)

#Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.connection.cursor()
    
    # Execute command
    cur.execute('DELETE FROM articles WHERE id = %s', [id])
    
    # Commit the change
    mysql.connection.commit()
    
    # Close connection
    cur.close()
    
    return redirect(url_for('dashboard'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
@app.route('/', methods=['GET', 'POST'])
@is_logged_in
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return 

#means that its the script to be executed
if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)