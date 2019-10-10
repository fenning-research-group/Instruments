import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

senderUsername = 'frgalerts'
senderAddress = 'frgalerts@gmail.com'
senderPassword = 'NanoPV2015'


def sendEmail(recepient, subject = '', body = ''):
	fromaddr = senderAddress
	server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
	server.login(senderUsername, senderPassword)
	
	msg = MIMEMultipart()
	msg['From'] = senderAddress
	msg['To'] = recepient
	msg['Subject'] = '[frgMapper] ' + subject
	body = body
	msg.attach(MIMEText(body, 'plain'))

	text = msg.as_string()
	try:
		server.sendmail(fromaddr, each_toaddr, text)
	except:
		print('Error encountered when sending email "{0}"'.format(subject))
		return False

	return True
