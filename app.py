from flask import Flask,request,render_template,redirect,url_for,flash,session,Response
from flask_session import Session
import os
import re
from otp import genotp
import bcrypt
from io import BytesIO
from stoken import token,dtoken
from cmail import send_mail
import mysql.connector
import razorpay
import pdfkit
app=Flask(__name__)
# config=pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
app.config['SESSION_TYPE']='filesystem'
RAZORPAY_KEY_ID='rzp_test_RXy19zNlFo9p8F'
RAZORPAY_KEY_SECRET='eIHxmEyJqhKz2l0tHEy7KkkC'
client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
app.secret_key=b'=\x9a\xdb\xd9\xcd'
Session(app)
# mydb=mysql.connector.connect(host='localhost',user='root',password='admin',db='ecommy')
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,port=port,db=db,user=user,password=password) as conn:
    cursor=conn.cursor()
    cursor.execute(" CREATE TABLE user (user_name varchar(100) NOT NULL,password varbinary(150) DEFAULT NULL,address tinytext,user_id int unsigned NOT NULL AUTO_INCREMENT,email varchar(30) NOT NULL,gender enum('male','female') DEFAULT NULL,PRIMARY KEY (user_id),UNIQUE KEY email (email))")

    cursor.execute(" CREATE TABLE admin (admin_name varchar(100) NOT NULL,email varchar(50) NOT NULL,password varbinary(150) DEFAULT NULL,image_name varchar(150) DEFAULT NULL,address tinytext,admin_id int unsigned NOT NULL AUTO_INCREMENT,PRIMARY KEY (admin_id),UNIQUE KEY email (email))")

    cursor.execute("  CREATE TABLE items ( itemid binary(16) NOT NULL,item_name longtext NOT NULL,description longtext NOT NULL,category enum('electronics','home','fashion','grocery') DEFAULT NULL,price bigint DEFAULT NULL,quantity int DEFAULT NULL,image_name varchar(200) DEFAULT NULL,added_by int unsigned DEFAULT NULL,PRIMARY KEY (itemid),KEY added_by (added_by),CONSTRAINT items_ibfk_1 FOREIGN KEY (added_by) REFERENCES admin (admin_id))")

    cursor.execute(" CREATE TABLE review (r_id int NOT NULL AUTO_INCREMENT,review_text text,itemid binary(16) DEFAULT NULL,added_by int unsigned DEFAULT NULL,created_at datetime DEFAULT CURRENT_TIMESTAMP, rating enum('1','2','3','4','5') DEFAULT NULL,title text NOT NULL,PRIMARY KEY (r_id),KEY itemid (itemid),KEY added_by (added_by),CONSTRAINT review_ibfk_1 FOREIGN KEY (itemid) REFERENCES items (itemid), CONSTRAINT review_ibfk_2 FOREIGN KEY (added_by) REFERENCES user (user_id))")

    cursor.execute(" CREATE TABLE orders (ord_id bigint NOT NULL AUTO_INCREMENT,item_name longtext,qyt int DEFAULT NULL,total_price bigint DEFAULT NULL,user int unsigned DEFAULT NULL,itemid binary(16) DEFAULT NULL,PRIMARY KEY (ord_id),KEY user (user),KEY items_od (itemid),CONSTRAINT items_od FOREIGN KEY (itemid) REFERENCES items (itemid) ON DELETE SET NULL,CONSTRAINT orders_ibfk_2 FOREIGN KEY (user) REFERENCES user (user_id)) ")

@app.route('/')
def home():
    return render_template('Welcome.html')
@app.route('/page',methods=['GET','POST'])
def page():
        return render_template('page.html')
@app.route('/admin_signup',methods=['GET','POST'])    
def admin_signup():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        address=request.form['address']
        image=request.files['img']
        imgname=genotp()+'.'+image.filename.split('.')[-1]
        path=os.path.dirname(os.path.abspath(__file__))
        static_path=os.path.join(path,'static')
        image.save(os.path.join(static_path,imgname))
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where email=%s',[email])
        countdata=cursor.fetchone()
        if countdata:
            if countdata[0]==0:
                otp=genotp()
                data={'username':username,'address':address,'email':email,'password':password,'imgname':imgname,'otp':otp}
                subject=' admin regestration otp for ecom app'
                body=f'OTP for admin Register{otp}'
                send_mail(to=email,subject=subject,body=body)
                #return (username,password,email,address,image)
                return redirect(url_for('adminverify',regdata=token(data=data)))
            elif countdata[0]==1:
                flash('email alredy existed')
                return redirect(url_for('alogin'))
        else:
            return 'Something went wrong'        

    return render_template('admin.html')    
@app.route('/adminverify/<regdata>',methods=['GET','POST'])
def adminverify(regdata)  :
    try:
        data=dtoken(data=regdata)
    except Exception as e:
            print(e)
            return 'somethingwent wrong'
    else:
        if request.method=='POST':
            uotp=request.form['otp']
            if uotp==data['otp']:
                try:
                    bytes=data['password'].encode('utf-8')
                    salt=bcrypt.gensalt()
                    #hashing the password
                    hash=bcrypt.hashpw(bytes,salt)
                    print(hash)
                    cursor=mydb.cursor(buffered=True) 
                    cursor.execute('insert into admin(admin_name,email,password,address,image_name)values(%s,%s,%s,%s,%s)',[data['username'],data['email'],hash,data['address'],data['imgname']])
                    mydb.commit()
                    cursor.close()
                    return redirect(url_for('alogin'))
                except Exception as e:
                    print(e)
                    return 'error'    
            else:
                return 'otp wrong'        
    return render_template('otp.html')
@app.route('/alogin',methods=['GET','POST'])
def alogin():
    if not session.get('admin'):
        if request.method=='POST':
            email=request.form['email']
            password=request.form['password'].encode('utf-8')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admin where email=%s',[email])
            countdata=cursor.fetchone()
            if countdata:
                if countdata[0]==1:
                    cursor.execute('select password from admin where email=%s',[email])
                    spassword=cursor.fetchone()[0]
                    if bcrypt.checkpw(password,spassword):
                        session['admin']=email
                        if not session.get('email'):
                            session[email]={}
                        return redirect(url_for('adashboard'))
                    else:
                        flash('password was incorrect')
                        return redirect(url_for('alogin'))
                flash('email not found')
                return redirect(url_for('alogin'))
            return 'something went wrong'    
        return render_template('adminlogin.html') 
    return redirect(url_for('adashboard'))
@app.route('/adashboard')
def adashboard():
    if session.get('admin'):
        return render_template('adashboard.html')
    return render_template('adashboard.html')
@app.route('/additem/',methods=['GET','POST'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            title=request.form['title']
            description=request.form['description']
            price=request.form['price']
            quantity=request.form['quantity']
            category=request.form['category']
            img=request.files['img']
            imgname=genotp()+'.'+img.filename.split('.')[-1]
            path=os.path.dirname(os.path.abspath(__file__))
            static_path=os.path.join(path,'static')
            img.save(os.path.join(static_path,imgname))
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select admin_id from admin where email=%s',[session.get('admin')])
                ad_id=cursor.fetchone()
                if ad_id:

                    cursor.execute('insert into items(itemid,item_name,description,category,price,quantity,image_name,added_by)values (uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[title,description,category,price,quantity,imgname,ad_id[0]])
                    mydb.commit()
                    cursor.close()
                    flash(f'item {title} addes successfully')
                    return redirect(url_for('additem'))
                else:
                    return 'pls login again something went wrong'
            except Exception as e:
                print(e)
                print("something went wrong")   
        return render_template('additem.html')
    return redirect(url_for('alogin'))
@app.route('/viewitems')
def viewitems():
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select admin_id from admin where email=%s',[session.get('admin')])
        ad_id=cursor.fetchone()
       
        if ad_id:
            cursor.execute('select bin_to_uuid(itemid),item_name,image_name from items where added_by=%s',[ad_id[0]])
            itemsdata=cursor.fetchall()
            print(itemsdata)
            if itemsdata:
                return render_template('card.html',itemsdata=itemsdata)
            else:
                return 'No items found'
        else:
            return 'user id not found'        
    return redirect(url_for('alogin'))
@app.route('/view_item/<itemid>')
def view_item(itemid):
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select admin_id from admin where email=%s',[session.get('admin')])
        ad_id=cursor.fetchone()
        if ad_id:
            cursor.execute('select bin_to_uuid(itemid),item_name,description,price,quantity,image_name,category,added_by from items where added_by=%s and itemid=uuid_to_bin(%s)',[ad_id[0],itemid])
            item_data=cursor.fetchone()
            if item_data:
                return render_template('view.html',item_data=item_data)
            else:
                return 'No item found'
        else:
            return 'user id not found'   
    return redirect(url_for('alogin'))     
@app.route('/update/<itemid>',methods=['GET','POST'])
def update(itemid):
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select admin_id from admin where email=%s',[session.get('admin')])
        ad_id=cursor.fetchone() 
        if ad_id:
            cursor.execute('select bin_to_uuid(itemid),item_name,description,price,quantity,image_name,category,added_by from items where added_by=%s and itemid=uuid_to_bin(%s)',[ad_id[0],itemid])
            item_data=cursor.fetchone()
            if request.method=='POST':
                title=request.form['title']
                description=request.form['description']
                price=request.form['price']
                quantity=request.form['quantity']
                category=request.form['category']
                img=request.files['img']
                if img.filename=='':
                    imgname=item_data[5]
                else:
                    imgname=genotp()+'.'+img.filename.split('.')[-1]
                    path=os.path.dirname(os.path.abspath(__file__))
                    static_path=os.path.join(path,'static')
                    os.remove(os.path.join(static_path,item_data[5]))
                    img.save(os.path.join(static_path,imgname)) 
                    cursor=mydb.cursor(buffered=True)   
                    cursor.execute('update items set item_name=%s,description=%s,price=%s,quantity=%s,image_name=%s,category=%s where itemid=uuid_to_bin(%s)',[title,description,price,quantity,imgname,category,itemid])
                    mydb.commit()
                    cursor.close()
                    flash(f'item {title} update successfully')
                    return redirect(url_for('update',itemid=itemid))

            if item_data:
                return render_template('update.html',item_data=item_data) 
            else:
                return 'no item found'
        return 'user id not found'
    
    return redirect('alogin')
@app.route('/delete/<itemid>')
def delete(itemid):
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select admin_id from admin where email =%s',[session.get('admin')])
        ad_id=cursor.fetchone()
        if ad_id:
            cursor.execute('select image_name from items where itemid=uuid_to_bin(%s)',[itemid])
            imgdata=cursor.fetchone()[0]
            path=os.path.dirname(os.path.abspath(__file__))
            static_path=os.path.join(path,'static')
            os.remove(os.path.join(static_path,imgdata))
            cursor.execute('delete from review where itemid=uuid_to_bin(%s)',[itemid])
            cursor.execute('delete from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,ad_id[0]])
      
            mydb.commit()
            cursor.close()
            flash(f'item delete successfully')
            return redirect(url_for('viewitems'))
        else:
            return 'user not found'
    return redirect(url_for('alogin'))  
@app.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('alogin')) 
    else:
        return redirect(url_for('alogin')) 
@app.route('/home1')
def home1():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(itemid),item_name,image_name,price from items')
    itemsdata=cursor.fetchall()
    print(itemsdata)
    return render_template('nav.html',itemsdata=itemsdata)
@app.route('/user_signup',methods=['GET','POST'])
def user_signup():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        address=request.form['address']
        gender=request.form['gender']
        
        otp=genotp()
        data={'username':username,'address':address,'email':email,'password':password,'otp':otp,'gender':gender}
        subject='user regestration form for otp'
        body=f'otp for user regestration {otp}'
        send_mail(to=email,subject=subject,body=body)
        return redirect(url_for('userverify',regdata=token(data=data)))
    return render_template('user.html')
@app.route('/userverify/<regdata>',methods=['GET','POST'])
def userverify(regdata):
        try:
            data=dtoken(data=regdata)
        except Exception as e:
            print(e)
            return 'Something went Wrong'
        else:
            if request.method=='POST':
                uotp=request.form['otp']
                if uotp==data['otp']:
                    try:
                        bytes=data['password'].encode('utf-8')
                        salt=bcrypt.gensalt()
                        #hashing the password
                        hash=bcrypt.hashpw(bytes,salt)
                        print(hash)
                        cursor=mydb.cursor(buffered=True)
                        cursor.execute('insert into user(user_name,password,address,email,gender) values(%s,%s,%s,%s,%s)',[data['username'],hash,data['address'],data['email'],data['gender']]) 
                        mydb.commit()
                        cursor.close()
                        return redirect(url_for('ulogin'))
                    except Exception as e:
                        print(e)  
                        return 'error'  
                else:
                    return 'otp wrong'
        return render_template('userotp.html') 

@app.route('/ulogin',methods=['POST','GET']) 
def ulogin():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password'].encode('utf-8')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from user where email=%s',[email])
        countdata=cursor.fetchone()
        if countdata:
            if countdata[0]==1:
                cursor.execute('select password from user where email=%s',[email])
                spassword=cursor.fetchone()[0]
                if bcrypt.checkpw(password,spassword):
                    session['user']=email
                    if not session.get(email):
                        session[email]={}
                    return redirect(url_for('home1'))
                else:
                    flash('password was incorrect')
                    return redirect(url_for('ulogin'))
            flash('email not found')
            return redirect(url_for('ulogin'))
        return 'something went wrong'    
    return render_template('ulogin.html') 
@app.route('/dashboard/<ctype>')
def dashboard(ctype):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(itemid),item_name,description,category,price,quantity,image_name,added_by from items where category=%s',[ctype])
    data=cursor.fetchall()
    return render_template('dashboard.html',data=data)
@app.route('/description/<itemid>')
def description(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(itemid),item_name,description,category,price,quantity,image_name,added_by from items where itemid=uuid_to_bin(%s)',[itemid])
    data=cursor.fetchone()
    return render_template('description.html',data=data)
#select * from items where itemid=uuid_to_bin(%s),[itemid]
@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            review=request.form['review']
            rating=request.form['rate']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select user_id from user where email=%s',[session.get('user')])
            u_id=cursor.fetchone()[0]
            cursor.execute('insert into review(title,review_text,rating,itemid,added_by) values(%s,%s,%s,uuid_to_bin(%s),%s)',[title,review,rating,itemid,u_id])
            mydb.commit()
            cursor.close()
            flash('review added sussessfully')
            return redirect(url_for('description',itemid=itemid))
        return render_template('review.html')   
    return redirect(url_for('ulogin')) 
@app.route('/addcart/<itemid>',methods=['GET','POST'])
def addcart(itemid):
    if session.get('user'):
        print(session)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,description,category,price,quantity,image_name,added_by from items where itemid=uuid_to_bin(%s)',[itemid])
        data=cursor.fetchone()
        item_name=data[1]
        category=data[3]
        price=data[4]
        if request.method=='POST':
            quantity=request.form['qyt']
        else:
            quantity=1
        image=data[6]
        if itemid not in session['user']:
            session[session.get('user')][itemid]=[item_name,price,quantity,image,category]
            session.modified=True
            print(session)
            flash(f'{item_name} added to cart')
            return redirect(url_for('home1'))
        session[session.get('user')][itemid][2]=+1
        flash('item alredy existed')
        return redirect(url_for('nav'))
    return redirect(url_for('ulogin'))
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('ulogin')) 
    else:
        return redirect(url_for('ulogin')) 
@app.route('/readreview/<itemid>')
def readreview(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('Select bin_to_uuid(itemid),item_name,description,category,price,quantity,image_name from items where itemid=uuid_to_bin(%s)',[itemid])
    data1=cursor.fetchone()
    cursor.execute('Select * from review where itemid=uuid_to_bin(%s)',[itemid])
    data2=cursor.fetchall()
    data=list(data1)+data2
    print(data)
    return render_template('readreview.html',data=data,data2=data2)      
@app.route('/viewcart')
def viewcart():
    if session.get('user'):
        if session.get(session.get('user')):
            items=session[session.get('user')]
            return render_template('cart.html',items=items)
        else:
            items='empty'   
        if items=='empty':    
            return 'NO product added'   
    return redirect(url_for('ulogin'))
@app.route('/removecart/<itemid>')
def removecart(itemid):
    if session.get('user'):
        session[session.get('user')].pop(itemid)
        session.modified=True
        return redirect(url_for('home1'))
    return redirect(url_for('ulogin')) 

@app.route('/pay/<itemid>/<name>/<int:price>',methods=['GET','POST'])
def pay(itemid,name,price):
    if session.get('user'):

        try:
            if request.method=='POST':
                qyt=int(request.form['qyt'])
            else:
                qyt=1
            #amount=price*100 # convert the price into paisa
            total_price=price*qyt
            print(price,qyt,total_price)
            print(f'creating payment for item:{itemid},name:{name},price:{total_price}')
            #creating Razorpay order
            order=client.order.create({
                'amount':total_price*100,
                'currency':'INR',
                'payment_capture':'1'
            })  
            print(f'order created:{order}')
            return render_template('pay.html',order=order,itemid=itemid,name=name,price=total_price,qyt=qyt)
        except Exception as e:
            print(e)
            return str(e),400
@app.route('/success',methods=['POST'])
def success():
    #extract payment details from the form
    payment_id =request.form.get('razorpay_payment_id')
    order_id=request.form.get('razorpay_order_id')
    signature=request.form.get('razorpay_signature')
    name=request.form['name']
    itemid=request.form['itemid']
    total_price=request.form['total_price']
    qyt=request.form['qyt']
    param_dict={
        'razorpay_payment_id':payment_id,
        'razorpay_order_id':order_id,
        'razorpay_signature':signature
       
    }   
    try:
        client.utility.verify_payment_signature(param_dict)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select user_id from user where email=%s',[session.get('user')])
        u_id=cursor.fetchone()[0]
        cursor.execute('insert into orders(itemid,item_name,total_price,user,qyt) values (uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,total_price,u_id,qyt]) 
        mydb.commit()
        cursor.close()
        flash('order placed successfully')
        return redirect(url_for('orders'))
    except Exception as e:
        print(e)
        return f'{e}',400
@app.route('/orders')
def orders():
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select user_id from user where email=%s',[session.get('user')])
        u_id=cursor.fetchone()
        cursor.execute('select * from orders where user=%s',[u_id[0]])
        user_orders=cursor.fetchall()
        cursor.close()
        return render_template('orders.html',user_orders=user_orders)
    return redirect(url_for('ulogin'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        name=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'{strg}',re.IGNORECASE)
        if (pattern.match(name)):
            cursor=mydb.cursor(buffered=True)
            query='select bin_to_uuid(itemid),item_name,description,category,price,quantity,image_name from items where item_name like %s or price like %s or description like %s or category like %s or quantity like %s'
            search_pram=f'%{name}%'
            cursor.execute(query,[search_pram,search_pram,search_pram,search_pram,search_pram])
            data=cursor.fetchall()
            return render_template('dashboard.html',data=data)
        else:
            flash('Result not found')
    return render_template('panel.html')
# @app.route('/billdetails/<ordid>.pdf')  
# def invoice(ordid):
#     if session.get('user'):
#         cursor=mydb.cursor(buffered=True)
#         cursor.execute('select * from orders where ord_id=%s',[ordid])
#         orders=cursor.fetchone()
#         userid=orders[4]
#         oname=orders[1]
#         qyt=orders[2]
#         cost=orders[3]
#         cursor.execute('select user_name,address,email from user where user_id=%s',[orders[4]])
#         data=cursor.fetchone()
#         uname=data[0]
#         address=data[1]
#         email=data[2]
#         html=render_template('bill.html',uname=uname,address=address,oname=oname,qyt=qyt,cost=cost,email=email)
#         pdf=pdfkit.from_string(html,False,configuration=config)
#         response=Response(pdf,content_type='application/pdf')
#         response.headers['Content-Disposition']='inline;filename=output.pdf'
#         return response


 
if __name__=='__main__': 
    app.run()  
        
        
        
 
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
     