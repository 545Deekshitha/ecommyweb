import smtplib
from email.message import EmailMessage
def send_mail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('deekshithakamaraju@gmail.com','mgnm nezm rdzq lojp')
    msg=EmailMessage()  #creating object to for class
    msg['FROM']='deekshithakamaraju@gmail.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.quit()