from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash,request
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
import smtplib
from flask_ckeditor import CKEditor
import os

logged_in = 0
current_user_id = None
on_blog = None
my_email = "killbusyness@gmail.com" 
app_password = "ikvm yiji dxtd kiph" 
app = Flask(__name__)
app.config['SECRET_KEY'] = "rahulsharma" 
# '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)
ckeditor = CKEditor(app)
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI',"sqlite:///posts.db") #sensative
db = SQLAlchemy(model_class=Base)
db.init_app(app)
# 'sqlite:///posts.db'

login_manager = LoginManager()
login_manager.init_app(app)


@app.context_processor
def common_variable():
    global logged_in
    return dict(logged_in=logged_in)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User,user_id)

def admin_only(function):
    @wraps(function)
    def wrapper(*args,**kwargs):
        if current_user_id != 1:
            return abort(404)
        return function(*args,**kwargs)
    return wrapper

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
        
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_by")
    
    
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
        
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_no: Mapped[int] = mapped_column(Integer) 
    comment_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_by = relationship("User", back_populates="comments")
    
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
with app.app_context():
    db.create_all()

@app.route('/register',methods = ['POST','GET'])
def register():
    form_instance = RegisterForm()
    if form_instance.validate_on_submit():
        entred_email = request.form.get('email')
        user_email = db.session.execute(db.select(User).where(User.email == entred_email)).scalar()
        if user_email == None:
            hashed_password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256',salt_length=8)
            new_user = User(name = request.form.get('name'), email = entred_email, password = hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            global logged_in,current_user_id
            logged_in = 1
            current_user_id = new_user.id
            return redirect(url_for('get_all_posts'))
        else:
            error = "This account already exists, Please try another one"
            return render_template('register.html',form = form_instance,error = error)
    return render_template("register.html",form = form_instance)


@app.route('/login', methods = ['POST','GET'])
def login():
    form_instance = LoginForm()
    if form_instance.validate_on_submit():
        entred_email = request.form.get('email')
        user = db.session.execute(db.select(User).where(User.email == entred_email)).scalar()
        if user != None:
            entered_password = request.form.get('password')
            if check_password_hash(user.password, entered_password):
                login_user(user)
                global logged_in,current_user_id
                logged_in = 1
                current_user_id = user.id
                return redirect(url_for('get_all_posts'))
            else:
                error = "Wrong password"
                return render_template('login.html',form = form_instance,error = error)
        else:
            error = '''Account does not exists'''
            return render_template('login.html',form = form_instance,error = error)
    return render_template("login.html",form = form_instance)

@app.route('/all_posts')
def get_all_posts():
    global on_blog
    on_blog = False
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    # print("current user id is ",current_user_id)
    return render_template("index.html", all_posts=posts, logged_in = logged_in, user_id = current_user_id) 



@app.route("/post/<int:post_id>",methods = ['GET','POST'])
def show_post(post_id):
    global on_blog ,current_user_id

    if (current_user_id == None) and (on_blog == True):
        return redirect(url_for('login'))
    else:
        comment_form_instance = CommentForm()
        requested_post = db.get_or_404(BlogPost, post_id)
        all_data = db.session.execute(db.select(Comment)).scalars().all()
        data = [comment for comment in all_data if comment.post_no == post_id]
    
    if comment_form_instance.validate_on_submit():
        new_comment = Comment(
            body = request.form.get('comment'),
            comment_by = current_user,
            post_no = post_id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post',post_id = post_id))
    on_blog = True
    return render_template("post.html", 
                           post=requested_post,comments = data, 
                           comment_form = comment_form_instance,
                           current_user_id = current_user_id)



@app.route("/new-post", methods=["GET", "POST"])
@admin_only #11
def add_new_post(): 
    if request.method == "POST":
        new_post = BlogPost(
        title=request.form['title'],
        subtitle=request.form['subtitle'],
        body=request.form['body'],
        img_url=request.form['img_url'], 
        author=current_user, 
        date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make_post.html")


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    # edit_form = CreatePostForm(
    #     title=post.title,
    #     subtitle=post.subtitle,
    #     img_url=post.img_url,
    #     author=post.author,
    #     body=post.body
    # )
    if request.method == "POST":
        print("before title get")
        post.title = request.form.get('title')

        print("before subtitle get")
        post.subtitle = request.form.get('subtitle')

        print("before body get")
        post.body = request.form.get('body')

        print("before img_url get")
        post.img_url = request.form.get('img_url')

        print("before author get")
        post.author = current_user
        db.session.commit()

        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make_post.html", 
                           is_edit=True,
                           post = post,
                           render_content = post.body)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/")
def about():
    year = date.today().year
    return render_template("about.html",year=year)


@app.route("/contact",methods = ['POST','GET'])
def contact():
    if request.method == "POST":  
        name = request.form['name']
        email = request.form['email']
        number = request.form['phone']
        message = request.form['message']
        smtp_connection = smtplib.SMTP("smtp.gmail.com")
        smtp_connection.starttls()
        smtp_connection.login(user=my_email, password=app_password)
        smtp_connection.sendmail(from_addr=email , to_addrs=my_email , msg=f"\nName: {name}\n\nEmail: {email}\n\nPhone: {number}\n\nMessage: {message}\n")
        smtp_connection.close()
    return render_template("contact.html")

@app.route('/logout')
def logout():
    global logged_in,current_user_id
    current_user_id = None
    logged_in = 0
    
    logout_user()
    return redirect(url_for('get_all_posts'))

if __name__ == "__main__":
    app.run(debug=True, port=5002)
